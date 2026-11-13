# hmipserver ChangeLog

Changes of `hmipserver`, the HmIP server (`HMIPServer.jar`) of eQ-3, which
is only provided as a binary. Newest version first.

Changes not yet released are collected under `Unreleased` and get the
OpenCCU-Base release they are part of when it is published.

## Unreleased

* update `HMIPServer.jar` to version 1.5.2-SNAPSHOT (build 6140 of
  2026-11-13) from eQ-3, together with `HMServer.jar` and
  `coupling/ESHBridge.jar` (homematicip/OpenCCU-Base#17). (@cn-eq3)
  * both jars finish their start again while rfd does not answer, as the
    jars before 1.5.1 did (OpenCCU/OpenCCU-Base#358);
  * an XML-RPC event receiver whose calls fail three times in a row is now
    removed (`Legacy.RemoveUnreachableClients`, on by default), so it is no
    longer called again with every event; a receiver that hangs in the device
    list of its own `init` no longer holds up the `init` of other receivers
    (OpenCCU/OpenCCU-Base#192);
  * a repeated `init` on the virtual devices no longer keeps every previous
    registration for good (OpenCCU/OpenCCU-Base#36);
  * no new or changed device descriptions; `ESHBridge.jar` without a code
    change.
* `crRFD.conf`: lower `Legacy.Client.Socket.Timeout` from 600000 to 30000 ms,
  so a call to an XML-RPC event receiver that accepts the connection and
  never answers ends after 30 seconds instead of 10 minutes. (@hobbyquaker)
* update `HMIPServer.jar` to version 1.5.1 (build 6137 of 2026-11-12) from
  eQ-3, together with `HMServer.jar` and `coupling/ESHBridge.jar`
  (homematicip/OpenCCU-Base#16). (@cn-eq3)
  * an XML-RPC event receiver that accepts a connection and never answers no
    longer holds up the events for the other receivers, also while it hangs in
    the device list of its own `init`; each call to it now times out after
    `Legacy.Client.Socket.Timeout` (OpenCCU/OpenCCU-Base#192); the receiver is
    not dropped after such a timeout and is called again with the next event;
  * a repeated `init` no longer leaves a connection and its file descriptors
    behind (OpenCCU/OpenCCU-Base#36);
  * `HMServer.jar`, which a system without an HmIP radio module runs for its
    virtual devices, is now built from the same 1.5.1 code base as
    `HMIPServer.jar` (Java 21);
  * both `HMIPServer.jar` and `HMServer.jar` now read the device lists of rfd
    and hs485d once at their start, for the virtual devices, and do not finish
    their start while a configured one does not answer (the previous jars
    started without them);
  * new device descriptions: HmIP-DRI2 (input module for DIN rail mount,
    2 channels) and HmIP-SMS2 (switch actuator for surface mounting,
    2 channels, so far only known as ELV-SH-SMS2);
  * updated device descriptions for the firmware from 1.2.0 on, the previous
    description kept for older firmware: ELV-SH-CAP, ELV-SH-CTH, ELV-SH-CTV
    (low battery limit, cyclic status messages), HmIP-FCI6 (alarm zones, event
    delay, LED and low battery settings), HmIPW-SCTHD (display content, heating
    and cooling enable on the temperature channel); ELV-SH-TACO the same from
    firmware 1.4.0 on (cyclic status messages);
  * updated device descriptions: HmIP-MIOB (up to 20 instead of 7 links on the
    climate control input channel), HmIP-ESI-IND now reports its device type as
    HmIP-ESI-I;
  * `ESHBridge.jar` without a code change.
* update `HMIPServer.jar` to the build of 2026-10-08 (build 5936, version
  1.5.1-SNAPSHOT) from eQ-3: avoid a security counter update with invalid
  values. (@cn-eq3)

## Older versions

Changes of earlier versions are only recorded in the git history of this
repository.
