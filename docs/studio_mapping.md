# Studio → Code Mapping

Odoo Studio stores its customizations in regular Odoo technical models. This
document explains how `odoo-studio-extractor` detects them and how each
artifact maps to code in a hand-written Odoo module.

## Detection heuristics

| Artifact        | Source model         | Detection criteria                                                                  |
|-----------------|----------------------|--------------------------------------------------------------------------------------|
| Custom model    | `ir.model`           | `model` starts with `x_` **or** `state == 'manual'`                                  |
| Custom field    | `ir.model.fields`    | `name` starts with `x_studio_`, **or** `state == 'manual'`, **or** field belongs to a custom model |
| Studio view     | `ir.ui.view`         | `arch_db` contains `x_studio_`, `name` ilike `studio`, `key` ilike `studio`, or `model` is custom |
| Server action   | `ir.actions.server`  | `model_name` is a custom model (or all, when no custom models found)                 |
| Automated rule  | `base.automation`    | `model_name` is a custom model (module `base_automation` must be installed)          |
| Window action   | `ir.actions.act_window` | `res_model` is a custom model                                                     |
| Menu            | `ir.ui.menu`         | `action` references a detected window action                                         |
| Access right    | `ir.model.access`    | `model_id` is a custom model                                                         |
| Record rule     | `ir.rule`            | `model_id` is a custom model                                                         |

> "Custom model" here means a model detected as Studio-like, **plus** any
> standard model that has at least one Studio-like field.

## Mapping to a hand-written module

When rebuilding Studio customizations as code, the typical layout is:

```
my_studio_rebuild/
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── <model>.py
├── views/
│   ├── <model>_views.xml
│   └── menus.xml
├── data/
│   └── automations.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
└── README.md
```

| Studio artifact            | Where it lives in the module                        |
|----------------------------|-----------------------------------------------------|
| Custom model               | `models/<model>.py` (a `models.Model` subclass)     |
| Studio field               | A field on the corresponding model class            |
| Studio view                | `views/<model>_views.xml` (`<record model='ir.ui.view'>`) |
| Window action              | `views/<model>_views.xml` (`ir.actions.act_window`) |
| Menu                       | `views/menus.xml` (`<menuitem>`)                    |
| Server action              | `data/server_actions.xml` or method on the model    |
| Automated rule             | `data/automations.xml` (`base.automation`)          |
| Access rights              | `security/ir.model.access.csv`                      |
| Record rules               | `security/security.xml` (`ir.rule`)                 |

## Naming conventions during migration

It is usually safer to **keep the `x_` / `x_studio_` field names** during the
first migration step so existing data remains addressable, then rename them in
a controlled second step (with a proper migration script).

## What this tool does **not** do

- It does not generate the Odoo module for you.
- It does not delete or disable Studio customizations.
- It does not parse view XML semantically.
- It does not analyze cross-module dependencies of computed fields.

These remain manual or future-roadmap items.
