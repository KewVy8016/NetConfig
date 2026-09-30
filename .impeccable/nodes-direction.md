# Nodes — Device Index

Scope: Nodes inventory and shared navigation; Operate mode. Preserve Add Node,
Node Detail and History functional workflows. No backend or API changes.

## Direction contract

THESIS: A readable device inventory is the entry to configuration, not a grid of
interchangeable cards or a tutorial dashboard. Cards remain an optional view.

OWN-WORLD: Graphite navigation, white work plane, cool gray separators, teal primary
actions, readable sans text and monospace endpoints. Flat surfaces, restrained corners.

STORY: Identify the real Node and latest checked status, open its configuration,
then retain the existing Preview → Apply → results → History workflow.

FIRST VIEWPORT: Left navigation; breadcrumb above a large Nodes heading; Add Node
at upper right; search and Table/Cards controls above aligned name, endpoint,
connection, status and action columns. Configure is primary; Delete subordinate.
No lower Configure a node panel. Row hover/focus reveals the active working row
without fabricating selection or device data; motion is limited to short control feedback.

FORM: Rack service index, grounded candidate 3; seed 5836b556. User selected Device
Index, removed the lower guide, and requested implementation on 2026-09-30.
Approved comp: .impeccable/mocks/decision/assigned-v2.png.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
