# Glassdome Frontend Audit

**Date:** 2024-11-27  
**Purpose:** Identify unused components, integrate with Registry, improve performance

---

## Current Routes & Pages

| Route | Page | API Endpoints | Status |
|-------|------|---------------|--------|
| `/` | Dashboard | `/api/registry/status` | ✅ ACTIVE - Uses Registry |
| `/lab` | LabCanvas | `/api/labs`, `/api/deployments` | ✅ ACTIVE - Core feature |
| `/lab/:labId` | LabCanvas | Same as above | ✅ ACTIVE |
| `/monitor` | LabMonitor | `/api/registry/*` | ✅ NEW - Registry UI |
| `/deployments` | Deployments | `/api/reaper/missions` | ⚠️ REVIEW - Uses Reaper API |
| `/platform/:platform` | PlatformStatus | `/api/platforms/*` | ⚠️ SLOW - Needs Registry |
| `/reaper` | ReaperDesign | `/api/reaper/*` | ✅ ACTIVE - Complex |
| `/whiteknight` | WhiteKnightDesign | `/api/reaper/*`, `/api/whiteknight/*` | ⚠️ PARTIAL |
| `/whitepawn` | WhitePawnMonitor | `/api/whitepawn/*` | ⚠️ NO REGISTRY |

---

## Component Inventory

### Pages (`src/pages/`)

| Component | Lines | Purpose | Status | Action |
|-----------|-------|---------|--------|--------|
| `Dashboard.jsx` | ~160 | Main dashboard | ✅ ACTIVE | Uses Registry now |
| `LabCanvas.jsx` | ~800 | Lab designer | ✅ ACTIVE | Core feature |
| `LabMonitor.jsx` | ~300 | Registry monitor | ✅ NEW | Registry UI |
| `Deployments.jsx` | ~210 | Reaper missions | ⚠️ CONFUSING | Rename or merge |
| `PlatformStatus.jsx` | ~430 | Platform VMs | ⚠️ SLOW | Needs Registry |
| `ReaperDesign.jsx` | ~900 | Vuln injection | ✅ ACTIVE | Large but functional |
| `WhiteKnightDesign.jsx` | ~300 | Validation | ⚠️ PARTIAL | Needs completion |
| `WhitePawnMonitor.jsx` | ~360 | Network monitor | ⚠️ NO REGISTRY | Needs integration |

### Shared Components (`src/components/`)

| Component | Purpose | Used By | Status |
|-----------|---------|---------|--------|
| `OverseerChat/*` | AI chat interface | App.jsx | ✅ ACTIVE |
| `NetworkMap.jsx` | Network visualization | WhitePawnMonitor | ✅ ACTIVE |
| `DemoShowcase/*` | Demo mode | Dashboard | ✅ ACTIVE |
| `LabTemplates.jsx` | Template selector | **NOBODY** | ❌ UNUSED |
| `QuickDeploy.jsx` | Single VM deploy | **NOBODY** | ❌ UNUSED |

### Hooks (`src/hooks/`)

| Hook | Purpose | Status |
|------|---------|--------|
| `useRegistry.js` | Registry API access | ✅ NEW |

---

## Issues Found

### 1. Unused Components (Delete or Roadmap)

**`LabTemplates.jsx`** - Lab template selector
- Calls `/api/labs/templates` - endpoint may not exist
- Never imported anywhere
- **Recommendation:** Move to `_deprecated/` or make roadmap

**`QuickDeploy.jsx`** - Single VM deploy
- Calls `/api/agents/{type}/create` - old agent pattern
- Never imported anywhere  
- **Recommendation:** Move to `_deprecated/`

### 2. Confusing Navigation

**`Deployments.jsx`** shows Reaper missions, not lab deployments
- Users expect to see deployed labs
- Actually shows vulnerability injection missions
- **Recommendation:** Rename to "Missions" or integrate with LabMonitor

### 3. PlatformStatus.jsx - Performance Issues

```javascript
// Current: Polls /api/platforms/proxmox/all-instances every 30s
const interval = setInterval(fetchStatus, 30000)
```

**Problems:**
- Calls platform API directly (slow, 2-5 second response)
- Doesn't use Registry (which updates every 1-10 seconds)
- No loading states during refresh

**Solution:** Switch to Registry API:
```javascript
// Use Registry instead
fetch('/api/registry/resources?platform=proxmox')
```

### 4. WhitePawnMonitor - No Registry Integration

Currently uses:
- `/api/whitepawn/status`
- `/api/whitepawn/deployments`
- `/api/whitepawn/alerts`

**Problem:** Operates independently of Registry, no unified view

**Solution:** Add Registry events panel, share data with LabMonitor

### 5. WhiteKnightDesign - Incomplete

Has two modes:
1. Mission validation (works)
2. Direct validation (partial)

Direct validation UI exists but engine integration incomplete.

---

## Recommended Changes

### Phase 1: Cleanup (30 min)

1. **Move unused components to `_deprecated/`:**
   ```
   src/components/LabTemplates.jsx → _deprecated/frontend/
   src/components/LabTemplates.css → _deprecated/frontend/
   src/components/QuickDeploy.jsx → _deprecated/frontend/
   src/components/QuickDeploy.css → _deprecated/frontend/
   ```

2. **Update nav labels for clarity:**
   - "Deployments" → "Missions" (or remove from nav)

### Phase 2: Registry Integration (2 hours)

1. **Update PlatformStatus.jsx:**
   ```javascript
   // Replace direct platform calls with Registry
   import { useResources } from '../hooks/useRegistry'
   
   const { resources, loading } = useResources({ platform: 'proxmox' })
   ```

2. **Add Registry panel to WhitePawnMonitor:**
   - Show lab VMs from Registry
   - Show drift alerts
   - Unified monitoring view

### Phase 3: UX Improvements (1 hour)

1. **Fix navigation confusion:**
   - Dashboard → Clear entry points
   - Lab Monitor → Live lab state (Registry)
   - Missions → Reaper missions (rename Deployments)
   - Platforms → Infrastructure view

2. **Add loading states:**
   - Skeleton loaders instead of spinners
   - Optimistic updates

---

## API Endpoint Mapping

### Currently Used by Frontend

| Endpoint | Used By | Status |
|----------|---------|--------|
| `/api/registry/status` | Dashboard, LabMonitor | ✅ NEW |
| `/api/registry/resources` | LabMonitor | ✅ NEW |
| `/api/registry/labs` | LabMonitor | ✅ NEW |
| `/api/registry/labs/{id}` | LabMonitor | ✅ NEW |
| `/api/registry/drift` | LabMonitor | ✅ NEW |
| `/api/labs` | LabCanvas | ✅ ACTIVE |
| `/api/deployments` | LabCanvas | ✅ ACTIVE |
| `/api/platforms/proxmox/all-instances` | PlatformStatus | ⚠️ SLOW |
| `/api/platforms/{p}/{i}/vms/{id}/{action}` | PlatformStatus | ✅ ACTIVE |
| `/api/reaper/missions` | Deployments, ReaperDesign | ✅ ACTIVE |
| `/api/reaper/exploits` | ReaperDesign | ✅ ACTIVE |
| `/api/reaper/stats` | ReaperDesign | ✅ ACTIVE |
| `/api/whitepawn/status` | WhitePawnMonitor | ✅ ACTIVE |
| `/api/whitepawn/deployments` | WhitePawnMonitor | ✅ ACTIVE |
| `/api/whitepawn/alerts` | WhitePawnMonitor | ✅ ACTIVE |
| `/api/whiteknight/status` | WhiteKnightDesign | ⚠️ PARTIAL |

### Should Switch to Registry

| Current | Replace With |
|---------|--------------|
| `/api/platforms/proxmox/all-instances` | `/api/registry/resources?platform=proxmox` |
| Manual VM state polling | WebSocket `/api/registry/ws/events` |

---

## File Structure After Cleanup

```
frontend/src/
├── pages/
│   ├── Dashboard.jsx        ✅ Keep
│   ├── LabCanvas.jsx        ✅ Keep
│   ├── LabMonitor.jsx       ✅ Keep (NEW)
│   ├── PlatformStatus.jsx   ⚠️ Update to use Registry
│   ├── ReaperDesign.jsx     ✅ Keep
│   ├── WhiteKnightDesign.jsx ⚠️ Complete or simplify
│   └── WhitePawnMonitor.jsx ⚠️ Integrate with Registry
├── components/
│   ├── OverseerChat/        ✅ Keep
│   ├── NetworkMap.jsx       ✅ Keep
│   ├── DemoShowcase/        ✅ Keep
│   ├── LabTemplates.jsx     ❌ Move to _deprecated
│   └── QuickDeploy.jsx      ❌ Move to _deprecated
├── hooks/
│   └── useRegistry.js       ✅ Keep (NEW)
└── styles/
    └── *.css                ✅ Keep (remove unused)
```

---

## Summary

| Category | Count |
|----------|-------|
| Active Pages | 6 |
| Pages Needing Work | 3 |
| Unused Components | 2 |
| New Components | 2 (LabMonitor, useRegistry) |

### Priority Actions

1. ✅ **Immediate:** Move unused components to `_deprecated/`
2. ✅ **High:** Fix PlatformStatus to use Registry (sluggish)
3. ✅ **Medium:** Integrate WhitePawn with Registry
4. ✅ **Low:** Updated Deployments to show Labs + Missions

### Completed Updates (2024-11-27)

**PlatformStatus.jsx:**
- Now uses Registry API for Proxmox (5s polling vs 30s)
- Falls back to platform API for AWS/Azure/ESXi
- Much faster response time

**WhitePawnMonitor.jsx:**
- Added Registry status card in sidebar
- New "Registry" tab showing lab state, VMs, drift
- Unified view of WhitePawn alerts + Registry drift
- Labs selectable from Registry

**Deployments.jsx:**
- Now shows both Labs AND Missions
- Filter tabs: All / Labs / Missions
- Lab cards styled differently from Mission cards
- Navigation to Lab Designer and Reaper from header

