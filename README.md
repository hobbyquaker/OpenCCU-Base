# OpenCCU-Base for openccu-lite

This is a fork of [OpenCCU/OpenCCU-Base](https://github.com/OpenCCU/OpenCCU-Base). Its branch `lite` is what
[openccu-lite](https://github.com/hobbyquaker/openccu-lite) builds the Homematic interface processes from: `rfd`,
`hs485d`, `multimacd` and their libraries, the HMIPServer jars, the device descriptions and the configuration
templates. openccu-lite is a CCU firmware without ReGaHss and without the CCU WebUI, so those parts of this repository
are not used there.

The fork is meant to stay as close to OpenCCU-Base as possible. It is not a separate project: everything that is useful
for OpenCCU goes upstream.

## What it carries

- **Upstream's changes to the components openccu-lite ships**, cherry-picked from OpenCCU-Base (`git cherry-pick -x`,
  so every such commit names its upstream commit).
- **Fixes that are on their way upstream.** They are offered to OpenCCU-Base as pull requests and stay here until
  upstream has them.
- **HMIPServer releases from eQ-3** ([homematicip/OpenCCU-Base](https://github.com/homematicip/OpenCCU-Base)), taken as
  published, sometimes before OpenCCU takes them. Since HMIPServer 1.5.1 this fork uses eQ-3's `HMServer.jar` as well;
  OpenCCU keeps its earlier one.
- **A few configuration defaults** for openccu-lite, for example the XML-RPC timeouts in `crRFD.conf`.

Each component's `CHANGELOG.md` under `src/` says what changed in it.

## Comparison with upstream

- **[The comparison page](https://openccu-lite.github.io/OpenCCU-Base/)** lists OpenCCU-Base's commits in the components
  openccu-lite ships, newest first, with a line where `lite` stands: what is above it has not been taken yet. It also
  says which of them OpenCCU's latest release and its master already have. It is refreshed every six hours.
- [All differences between upstream's `main` and `lite`](https://github.com/OpenCCU/OpenCCU-Base/compare/main...openccu-lite:OpenCCU-Base:lite)
  on GitHub.
- How openccu-lite as a whole differs from OpenCCU:
  [openccu-lite's upstream delta](https://github.com/hobbyquaker/openccu-lite/blob/main/docs/upstream-delta.md).

## Branches and tags

| Branch | Holds |
| --- | --- |
| `lite` | what openccu-lite builds (the default branch) |
| `filtered` | upstream's history limited to the paths openccu-lite builds from; a read-only view, rewritten when the path list changes |
| `gh-pages` | the comparison page |
| `main` | an older copy of upstream's `main`; not maintained |
| others | the branches of pull requests to OpenCCU-Base |

Every openccu-lite release tags the `lite` commit it was built from with its own version, for example `v2.0.0-beta.3`,
and openccu-lite pins that tag.

## Issues

- Problems with openccu-lite: [openccu-lite's issues](https://github.com/hobbyquaker/openccu-lite/issues).
- Problems in the components themselves that affect OpenCCU as well:
  [OpenCCU-Base's issues](https://github.com/OpenCCU/OpenCCU-Base/issues).

## Licence

Unchanged from OpenCCU-Base: the components keep their licences, see [licenses/licenses.md](licenses/licenses.md) and
the texts in [licenses/](licenses/). Upstream's own description of this repository is in
[its README](https://github.com/OpenCCU/OpenCCU-Base/blob/main/README.md).
