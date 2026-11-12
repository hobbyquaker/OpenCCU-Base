# hmipserver ChangeLog

Changes of `hmipserver`, the HmIP server (`HMIPServer.jar`) of eQ-3, which
is only provided as a binary. Newest version first.

Changes not yet released are collected under `Unreleased` and get the
OpenCCU-Base release they are part of when it is published.

## Unreleased

* update `HMIPServer.jar` to version 1.5.1 (build 6137 of 2026-11-12) from
  eQ-3, together with `HMServer.jar` and `coupling/ESHBridge.jar`
  (homematicip/OpenCCU-Base#16). (@cn-eq3)
  * an XML-RPC event receiver that accepts a connection and never answers no
    longer holds up the events for the other receivers, also while it hangs in
    the device list of its own `init`; each call to it now times out after
    `Legacy.Client.Socket.Timeout` (600 seconds in the shipped `crRFD.conf`)
    (OpenCCU/OpenCCU-Base#192);
  * a repeated `init` no longer leaves a connection and its file descriptors
    behind (OpenCCU/OpenCCU-Base#36);
  * `HMServer.jar`, which a system without an HmIP radio module runs for its
    virtual devices, is now built from the same 1.5.1 code base as
    `HMIPServer.jar` (Java 21); unlike the previous one it stops at its start
    when BidCos-RF is configured and rfd does not answer;
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
