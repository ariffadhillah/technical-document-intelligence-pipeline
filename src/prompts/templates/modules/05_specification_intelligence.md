# Technical Specification and Commercial Value Extraction

Extract every explicitly stated technical specification, including:

- dimensions
- weights
- payloads
- capacities
- displacement
- engine power
- torque
- voltage
- current
- pressure
- tire dimensions
- wheel dimensions
- tank capacity
- gear count
- axle configuration
- production year
- quantities
- temperatures
- tolerances
- material specifications
- model identifiers
- product identifiers

Create a separate `technical_specifications` record for every distinct
technical value.

Do not omit a specification merely because the same value also appears in:

- vehicle data
- engine data
- transmission data
- part data
- service descriptions

Preserve the original displayed value and unit.

Add normalized values only when deterministic and unambiguous.

## Prices and commercial values

Extract prices only when the schema provides a suitable field, such as an
organization service.

Preserve:

- numeric amount
- currency
- price basis
- tax or VAT qualifier when stated
- whether it is an example price

Do not infer missing currency.

Do not treat a historical example price as a current market price.