# Upstream-Meldungen für Zendure-HA-zenSDK (Gielz1986)

Zwei getrennte Issues plus eine Rückfrage. Beobachtet auf Home Assistant 2026.8.2 /
HAOS 18.2, Paketversion **v20260824**, Datei
`Global (EN) Integration/packages/zendure_gielz1986_global.yaml`.

Beide Punkte sind lokal nur durch Auskommentieren zu beheben — und das geht beim
nächsten Paket-Update verloren. Deshalb upstream.

---

## Issue 1 — HomeWizard P1 REST resource floods the log when the IP helper is unset

**Title:** `HomeWizard P1 REST resource polls http://unknown/ when the IP helper is not set`

### What happens

`zendure_gielz1986_global.yaml` defines a second REST resource for a HomeWizard P1
meter (line 2331 in v20260824):

```yaml
- resource_template: "http://{{ states('input_text.homewizard_setting_p1_ip_address') }}/api/v1/data"
  scan_interval: 1
  sensor:
    - name: "Homewizard P1 Power"
      ...
```

`input_text.homewizard_setting_p1_ip_address` ships empty. On an installation that
does not use a HomeWizard P1, `states()` returns the literal string `unknown`, so the
template renders `http://unknown/api/v1/data` and the platform keeps polling that
hostname forever.

### Impact

On my installation this single resource produced **1252 of 1487 log lines** in a
41-hour window — about **84 %** of everything Home Assistant logged:

```
Error fetching data: http://unknown/api/v1/data failed with
  Cannot connect to host unknown:80 ssl:default [Timeout while contacting DNS servers]   ×1145
Error fetching data: http://unknown/api/v1/data failed with
  [DNS server returned answer with no data]                                              ×105
Platform rest not ready yet: Cannot connect to host unknown:80 ...                       ×57
```

`sensor.homewizard_p1_power` is never registered, so the block never does anything —
it only produces noise. The practical cost is that real faults become hard to find and
the log rotates away quickly.

### Why it cannot be fixed downstream

- Filling the helper does not help without the hardware — the DNS error just becomes a
  connection error.
- Home Assistant merges `rest:` lists additively; a package entry cannot be removed or
  overridden from another package or from `configuration.yaml`.
- Silencing `homeassistant.components.rest.data` via `logger:` would also hide the
  genuine Zendure errors.
- Commenting out the block locally works, but is lost on every package update.

### Suggested fix

Any of these would do:

1. Ship the HomeWizard block commented out, with a note in the README that it can be
   enabled by users who have the device.
2. Move it to a separate optional package file, e.g. `zendure_homewizard_p1.yaml`.
3. Guard the resource so it does not poll while the helper is unset — for example by
   giving the helper a harmless default that fails fast, or by documenting that it must
   be filled before first start.

Option 1 or 2 would be the least surprising for users who do not run a HomeWizard.

---

## Issue 2 — Template conditions use `| float` without a default and error when REST sensors go unavailable

**Title:** `Template errors in automation_global.yaml when Zendure REST sensors go unavailable (| float without default)`

### What happens

Several template conditions in the global automation render `| float` without a
default value. When the Zendure REST sensors briefly go `unavailable` — which happens
whenever a request to the device times out — the template raises:

```
Template error: float got invalid input 'unavailable' when rendering template
'{{ states('sensor.zendure_set_charge_power') | float != states('input_number.zendure_setting_max_charge_power') | float }}'
but no default was specified
```

Example (line 674 in v20260824):

```jinja
{{ states('sensor.zendure_set_charge_power') | float !=
   states('input_number.zendure_setting_max_charge_power') | float }}
```

### Scope

Counted in a clone of v20260824: **13 occurrences of `| float }}` without a default**,
against **56 occurrences of the correct `float(...)` form** elsewhere in the same file.
So this looks like an oversight in a codebase that otherwise gets it right.

### Impact

Limited but visible: the affected `choose` branch is skipped for that run and a WARNING
is logged; the next 5-second cycle recovers. On my installation the errors arrive in
bursts, each burst following a `sensor.zendure_total_state_of_charge` dropout — for
example a request timeout at `07:29:39.384`, the sensor going `unavailable` at
`07:29:39.424`, and the template errors at `07:29:40`.

### Suggested fix

Add an explicit default to the affected expressions:

```jinja
{{ states('sensor.zendure_set_charge_power') | float(0) !=
   states('input_number.zendure_setting_max_charge_power') | float(0) }}
```

Choosing `0` versus some other sentinel is a judgement call per condition — in some of
them a wrong default might flip the branch, so it is worth a quick look rather than a
blanket replace.

---

## Rückfrage (kein Issue) — `scan_interval: 1` without `timeout`

The Zendure resource (line 1487) polls `/properties/report` every second and sets no
`timeout`, so Home Assistant's 10-second default applies:

```yaml
- resource_template: "http://{{ states('input_text.zendure_setting_ip_address') }}/properties/report"
  scan_interval: 1
```

On my SolarFlow 2400 Pro this occasionally produces `Server disconnected` and timeout
errors — 7 in about 27 hours — each of which drops the whole Zendure sensor set to
`unavailable` for roughly one cycle and triggers the template errors from Issue 2.
Home Assistant also logs `Updating state for sensor.zendure_battery_5_temperature took
2.136 seconds`, so the device sometimes needs over two seconds to answer a request that
arrives every second.

The network side looks healthy: the device tracker stays `home` throughout, WiFi signal
is reported as Good/Excellent, and recovery happens after a single cycle.

Not filing this as a defect — the one-second interval is presumably deliberate, since
the control automation runs on a 5-second cycle. But is a slower interval or an explicit
`timeout:` something you would consider, or is the current setting needed for the
control loop to behave?

---

## Kontext, der nicht ins Issue gehört

Nur zur eigenen Erinnerung, nicht mitschicken:

- Die ursprüngliche Vermutung, der `rest:`-Block existiere doppelt in der lokalen
  Konfiguration, ist widerlegt — die Suche über `/config` ergab genau einen Treffer für
  `properties/report`. Die 50 Unique-ID-Kollisionen vom 31.08. um 12:15:46 traten drei
  Sekunden nach einem Reload auf und sind vermutlich ein Artefakt des Neuaufbaus der
  REST-Plattform, nicht der Beleg für eine Doppelung.
- Beide Issues betreffen ausschliesslich Fremdcode. In der eigenen Konfiguration gibt
  es dafür keine updatefeste Korrektur.
