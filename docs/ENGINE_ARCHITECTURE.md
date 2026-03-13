# Engine Architecture - V168.000 [Genesis.Solidify]

=====================================================

This document outlines the architecture of the `src/infrastructure/engines` module, focusing on the relationship between `QuantHarvester`, `SurgicalInteraction`, and specialized sub-modules.

## 1. High-Level Overview

The harvest engine follows a facade pattern where `SurgicalInteraction` coordinates specialized modules for browser interactions.

```mermaid
graph TD
    QH[QuantHarvester.js] --> |Uses| SI[SurgicalInteraction.js]
    QH --> |Uses| SR[SignalRadar.js]
    QH --> |Uses| EC[EngineConfig.js]
    
    SI --> |Delegates to| AF[AntiFingerprint.js]
    SI --> |Delegates to| DN[DOMNavigator.js]
    SI --> |Delegates to| ES[EventSimulator.js]
    
    SR --> |Injects| TH[TitanHeart (Browser Context)]
```

## 2. Core Modules

### 2.1 QuantHarvester (`src/infrastructure/engines/QuantHarvester.js`)

**Role:** Main orchestrator for batch processing.

- Manages concurrency (p-limit).
- Handles DB transactions (Pool).
- Implements "Fast Fail" & "Auto-Healing" logic.
- Integrates `SignalRadar` for network interception.

### 2.2 SurgicalInteraction (`src/infrastructure/engines/services/SurgicalInteraction.js`)

**Role:** Browser interaction facade.

- **Responsibility:** High-level API for interacting with the page (hover, click, extract).
- **Sub-modules:**
  - `AntiFingerprint`: Hides bot signature (Overlay removal, CSS injection).
  - `DOMNavigator`: Finds elements and extracting text (Modal detection, Provider mapping).
  - `EventSimulator`: Simulates human actions (Hover, Jitter, Wait).

### 2.3 SignalRadar (`src/infrastructure/engines/services/SignalRadar.js`)

**Role:** Network interception & Data extraction.

- **Responsibility:** Captures WebSocket/XHR data.
- **Features:**
  - `TitanHeart`: In-browser hook for data capture.
  - `TriggerMode`: Synchronization between action and data arrival.

## 3. Specialized Modules (`src/infrastructure/engines/services/modules/`)

### 3.1 AntiFingerprint (`anti_fingerprint.js`)

- **Purpose:** Bypass anti-bot measures.
- **Key Methods:**
  - `handleOverlays()`: Brute force removal of cookie banners/ads.
  - `scrollSettle()`: Human-like scrolling behavior.

### 3.2 DOMNavigator (`dom_navigator.js`)

- **Purpose:** Understanding the page structure.
- **Key Methods:**
  - `detectModalWithTitle()`: Finds the odds history modal.
  - `extractProviderNameFromCell()`: Maps a cell to its bookmaker (Pinnacle, bet365, etc.).

### 3.3 EventSimulator (`event_simulator.js`)

- **Purpose:** Realistic user interaction.
- **Key Methods:**
  - `performReliableHover()`: Safe hovering with retry logic.
  - `waitForMemoryData()`: Zero-latency check for captured data.
  - `generatePixelJitter()`: Random mouse movement noise.

## 4. Configuration

All engine configuration is centralized in `src/infrastructure/engines/config/EngineConfig.js`.

- **Concurrency:** `MAX_CONCURRENT_BROWSERS`
- **Timeouts:** `RENDER_WINDOW`, `MEMORY_HOOK_TIMEOUT`
- **Feature Flags:** `FORCE_REMOVE_OVERLAYS`

## 5. Flow Diagram (Single Match)

1. **Launch:** `QuantHarvester` starts browser.
2. **Inject:** `SignalRadar` injects hooks.
3. **Navigate:** Page loads.
4. **Purge:** `SurgicalInteraction` -> `AntiFingerprint` removes overlays.
5. **Trigger:** `SignalRadar` enables trigger mode.
6. **Action:** `SurgicalInteraction` hovers/clicks via `EventSimulator`.
7. **Capture:** Network data captured by `SignalRadar`.
8. **Parse:** `TrajectoryParser` processes data.
9. **Store:** Data saved to DB.
