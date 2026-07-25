# Document Intelligence

Determine the nature of the supplied material before extracting knowledge.

Possible source types include:

- forum discussion
- technical manual
- workshop manual
- maintenance guide
- service report
- inspection report
- engineering drawing
- schematic
- brochure
- company profile
- advertisement
- quotation
- invoice
- product catalogue
- parts catalogue
- product datasheet
- regulation
- standard
- book
- presentation
- scanned archival document
- mixed-source technical collection

The supplied document type metadata may describe the container rather than
every attachment. A forum thread may contain brochures, quotations,
photographs, scanned technical documents, or advertisements.

Apply extraction priorities according to the content:

## Forum discussion

Prioritize:

- confirmed technical facts
- recommendations
- disputed claims
- user experiences
- warnings
- maintenance and modification advice
- referenced products, organizations, and documents

Do not present forum opinion as established fact.

## Brochure or company profile

Prioritize:

- official organization identity
- contact details
- locations
- products
- services
- technical capabilities
- represented brands
- partner organizations
- commercial examples
- certifications
- document references

## Quotation or commercial technical document

Prioritize:

- supplier or fabricator identity
- customer identity when explicitly shown
- quoted products and services
- quantities
- prices and currency
- technical scope
- specifications
- exclusions
- optional items
- dates and identifiers

## Technical manual or service document

Prioritize:

- procedures
- specifications
- tools
- parts
- warnings
- diagnostic guidance
- compatibility
- document identifiers

## Scanned or OCR-derived source

Treat uncertain characters conservatively and reduce confidence when
the text is damaged or ambiguous.