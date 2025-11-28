"""
Confusion Detector module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

from typing import Dict, Any, Optional, List
import re


class ConfusionDetector:
    """Detect when agent needs RAG assistance"""
    
    # Patterns that indicate confusion/uncertainty
    ERROR_PATTERNS = [
        r"error",
        r"exception",
        r"failed",
        r"cannot",
        r"unable to",
        r"not found",
        r"timeout",
        r"refused",
        r"denied",
    ]
    
    UNCERTAINTY_PHRASES = [
        "i don't know",
        "i'm not sure",
        "i don't have",
        "unclear",
        "uncertain",
        "might be",
        "possibly",
        "unsure",
    ]
    
    HISTORICAL_QUESTIONS = [
        "why did",
        "how did",
        "what happened",
        "last time",
        "previously",
        "before",
        "history",
        "similar",
    ]
    
    CORRECTION_INDICATORS = [
        "actually",
        "no,",
        "that's wrong",
        "incorrect",
        "fix that",
        "change that",
        "should be",
        "supposed to",
    ]
    
    @staticmethod
    def should_query_rag(
        context: Dict[str, Any],
        query_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Determine if RAG should be queried
        
        Args:
            context: Current situation context
                - user_message: What user said
                - agent_response: What agent is about to say
                - error_message: Any error that occurred
                - confidence_score: Agent's confidence (0-1)
                - task: Current task being attempted
                
            query_type: Override detection ("auto", "force", "never")
            
        Returns:
            {
                "should_query": bool,
                "reason": str,
                "query_suggestion": str,
                "priority": str (low/medium/high)
            }
        """
        if query_type == "force":
            return {
                "should_query": True,
                "reason": "Forced query",
                "query_suggestion": context.get("user_message", ""),
                "priority": "high"
            }
        
        if query_type == "never":
            return {
                "should_query": False,
                "reason": "RAG disabled",
                "query_suggestion": None,
                "priority": "none"
            }
        
        # Check various confusion indicators
        checks = [
            ConfusionDetector._check_error(context),
            ConfusionDetector._check_uncertainty(context),
            ConfusionDetector._check_historical_question(context),
            ConfusionDetector._check_correction(context),
            ConfusionDetector._check_low_confidence(context),
            ConfusionDetector._check_unknown_entity(context),
        ]
        
        # Return first positive check
        for check in checks:
            if check["should_query"]:
                return check
        
        # No confusion detected
        return {
            "should_query": False,
            "reason": "No confusion detected",
            "query_suggestion": None,
            "priority": "none"
        }
    
    @staticmethod
    def _check_error(context: Dict) -> Dict:
        """Check if an error occurred"""
        error_msg = context.get("error_message", "")
        
        if not error_msg:
            return {"should_query": False}
        
        # Check if error matches known patterns
        for pattern in ConfusionDetector.ERROR_PATTERNS:
            if re.search(pattern, error_msg, re.IGNORECASE):
                return {
                    "should_query": True,
                    "reason": f"Error encountered: {error_msg[:100]}",
                    "query_suggestion": f"How to fix error: {error_msg}",
                    "priority": "high"
                }
        
        return {"should_query": False}
    
    @staticmethod
    def _check_uncertainty(context: Dict) -> Dict:
        """Check if agent expressed uncertainty"""
        agent_response = context.get("agent_response", "").lower()
        
        for phrase in ConfusionDetector.UNCERTAINTY_PHRASES:
            if phrase in agent_response:
                return {
                    "should_query": True,
                    "reason": f"Agent uncertain: '{phrase}'",
                    "query_suggestion": context.get("task", context.get("user_message", "")),
                    "priority": "medium"
                }
        
        return {"should_query": False}
    
    @staticmethod
    def _check_historical_question(context: Dict) -> Dict:
        """Check if user asked about history/past events"""
        user_msg = context.get("user_message", "").lower()
        
        for phrase in ConfusionDetector.HISTORICAL_QUESTIONS:
            if phrase in user_msg:
                return {
                    "should_query": True,
                    "reason": f"Historical question: '{phrase}'",
                    "query_suggestion": user_msg,
                    "priority": "high"
                }
        
        return {"should_query": False}
    
    @staticmethod
    def _check_correction(context: Dict) -> Dict:
        """Check if user corrected the agent"""
        user_msg = context.get("user_message", "").lower()
        
        for phrase in ConfusionDetector.CORRECTION_INDICATORS:
            if user_msg.startswith(phrase):
                return {
                    "should_query": True,
                    "reason": "User corrected agent",
                    "query_suggestion": f"Context for: {user_msg}",
                    "priority": "high"
                }
        
        return {"should_query": False}
    
    @staticmethod
    def _check_low_confidence(context: Dict) -> Dict:
        """Check if agent has low confidence"""
        confidence = context.get("confidence_score", 1.0)
        
        if confidence < 0.5:
            return {
                "should_query": True,
                "reason": f"Low confidence: {confidence:.2f}",
                "query_suggestion": context.get("task", ""),
                "priority": "medium"
            }
        
        return {"should_query": False}
    
    @staticmethod
    def _check_unknown_entity(context: Dict) -> Dict:
        """Check if agent encountered unknown VM/platform/config"""
        user_msg = context.get("user_message", "")
        
        # Check for mentions of VMs, platforms, etc.
        vm_pattern = r"VM\s+\d+|vm\s+\d+"
        platform_pattern = r"(proxmox|esxi|aws|azure)"
        
        if re.search(vm_pattern, user_msg, re.IGNORECASE):
            return {
                "should_query": True,
                "reason": "Query about specific VM",
                "query_suggestion": user_msg,
                "priority": "medium"
            }
        
        if re.search(platform_pattern, user_msg, re.IGNORECASE):
            task = context.get("task", "")
            if "deploy" in task.lower() or "configure" in task.lower():
                return {
                    "should_query": True,
                    "reason": "Platform-specific task",
                    "query_suggestion": f"{task} best practices",
                    "priority": "medium"
                }
        
        return {"should_query": False}


# Example usage patterns
if __name__ == "__main__":
    print("=== Confusion Detector Examples ===\n")
    
    # Test 1: Error scenario
    context1 = {
        "error_message": "VM failed to boot after 3 attempts",
        "task": "deploy ubuntu to proxmox"
    }
    result1 = ConfusionDetector.should_query_rag(context1)
    print(f"Test 1 (Error): {result1}\n")
    
    # Test 2: Historical question
    context2 = {
        "user_message": "Why did VM 114 fail initially?",
        "agent_response": ""
    }
    result2 = ConfusionDetector.should_query_rag(context2)
    print(f"Test 2 (Historical): {result2}\n")
    
    # Test 3: Uncertainty
    context3 = {
        "agent_response": "I'm not sure which VLAN tag to use",
        "task": "deploy VM to 192.168.3.x"
    }
    result3 = ConfusionDetector.should_query_rag(context3)
    print(f"Test 3 (Uncertainty): {result3}\n")
    
    # Test 4: Correction
    context4 = {
        "user_message": "Actually, that's wrong. The credentials are in .env file.",
        "agent_response": "Loading from ~/.bashrc..."
    }
    result4 = ConfusionDetector.should_query_rag(context4)
    print(f"Test 4 (Correction): {result4}\n")
    
    # Test 5: No confusion
    context5 = {
        "user_message": "Deploy Ubuntu to Proxmox",
        "agent_response": "Deploying Ubuntu VM to Proxmox now...",
        "confidence_score": 0.95
    }
    result5 = ConfusionDetector.should_query_rag(context5)
    print(f"Test 5 (No confusion): {result5}\n")

