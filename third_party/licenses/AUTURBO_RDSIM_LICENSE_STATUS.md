# Upstream Provenance and License Status: AuTURBO / RDSim

## Summary

* **Upstream Repository**: `https://github.com/AuTURBO/RDSim.git`
* **Base Branch**: `devel/2wheel_diff`
* **Base Commit**: `335fb578ee35db732542c4459f23c8e4ca7716e5` (March 5, 2025)
* **Maintainers / Authors**: `ggh-png` (`0380089@gmail.com`), `KDW` (`msd030428@gmail.com`)
* **Upstream License File**: None present in root of `AuTURBO/RDSim` repository.
* **Package Declarations**:
  * `rdsim_gazebo/package.xml`: `<license>TODO: License declaration</license>`
  * `rdsim_description/package.xml`: `<license>TODO: License declaration</license>`
  * `rdsim_interfaces/package.xml`: `<license>Apache-2.0</license>`

## Upstream Clarification Inquiry

On November 1, 2026, the following formal communication was prepared for the maintainers of AuTURBO/RDSim:

```text
Title: License clarification for RDSim (and downstream use)

Hello, and thank you for publishing RDSim.

I maintain Chiheb-bt/NexusDelivery-Autonomous-AMR, a public repository. Comparing it with AuTURBO/RDSim (branch devel/2wheel_diff, commit 335fb57), about 2,480 tracked files are identical to yours and 14 are modified versions of yours (rdsim_description, rdsim_gazebo, rdsim_interfaces, launch files, a world file, the URDF). My repository is currently published under Apache-2.0.

I could not find a LICENSE file in RDSim, and two package.xml files say "TODO: License declaration" (rdsim_interfaces declares Apache-2.0).

I should have asked before redistributing these files. Could you tell me under which terms they may be used and redistributed, or confirm that you do not grant permission?

In the meantime I am adding a notice to my README, and I will remove or replace the RDSim-derived files if I do not have permission within 14 days. Thank you for your time.
```

## Remediation Policy
If explicit open-source licensing permission is not confirmed within 14 days, the `rdsim_*` scaffolding packages will be fully replaced with clean-room original packages (`nexus_description`, `nexus_gazebo`, `nexus_interfaces`), and OSRF assets will be downloaded at build time rather than bundled.
