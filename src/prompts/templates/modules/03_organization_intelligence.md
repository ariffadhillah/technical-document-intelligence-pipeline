# Organization Intelligence Extraction

Inspect the entire source, including:

- forum posts
- attachment text
- PDF text
- OCR text
- headers
- footers
- letterheads
- contact blocks
- advertisements
- brochures
- quotation pages
- signature blocks
- captions
- URLs
- email addresses
- telephone numbers
- fax numbers
- postal addresses
- visible company descriptions

Organizations may include:

- manufacturers
- component suppliers
- fabricators
- engineering companies
- workshops
- repair companies
- restoration companies
- dealers
- distributors
- service centers
- coating and painting companies
- body builders
- logistics companies
- government agencies
- military organizations
- standards organizations
- certification bodies
- partner companies

Populate `organizations` for every explicitly named organization that has
technical, commercial, service, manufacturing, supplier, or reference
relevance to the source.

For every organization, extract when explicitly supported:

- official or displayed name
- normalized name
- organization type
- description
- country
- city
- postal address
- telephone number
- mobile number
- fax number
- email address
- website
- products
- services
- technical capabilities
- engineering capabilities
- manufacturing capabilities
- repair capabilities
- restoration capabilities
- surface treatment capabilities
- represented brands
- certifications
- explicitly stated partner relationships
- associated vehicles
- associated engines
- associated transmissions
- associated components

Populate `contacts` when the source contains an actual contact method,
contact person, organization contact block, address, email, telephone,
mobile number, fax number, website, or coordinate.

An organization may be populated even when it has no direct contact method,
provided it is explicitly named and technically relevant.

Do not classify an ordinary forum participant as a supplier, workshop,
fabricator, employee, or specialist unless the source explicitly identifies
that role.

Do not reconstruct an organization whose name was removed or anonymized.

## Organization services

Create separate service records for distinct offerings such as:

- sandblasting
- priming
- painting
- industrial coating
- welding
- vehicle restoration
- chassis refurbishment
- special-purpose vehicle conversion
- component reproduction
- reverse engineering
- spare-part manufacturing
- technical inspection
- maintenance
- repair
- engineering design

When a service has an explicitly stated example price, preserve:

- original price
- currency
- stated basis or condition
- whether VAT or tax treatment is stated

Do not convert example prices into general fixed prices.

## Organization relationships

Record a relationship only when the source explicitly supports it.

Examples include:

- partner
- supplier
- distributor
- represented brand
- manufacturer
- service provider
- parent company
- subsidiary

A list headed with wording equivalent to "our partners" supports a partner
relationship.

Do not infer a partnership merely because two names appear on the same page.