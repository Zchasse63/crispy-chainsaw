# GoShip GraphQL API Reference

## Endpoint
```
POST https://nautilus.goship.com/broker/graphql
```

## Authentication
Header: `X-GoShip-API-Key: <your-api-key>`

## Request LTL Quote Query

### Query Structure
```graphql
query RequestLTLQuote($rfq: LtlRfqInput!) {
  requestLTLQuote(rfq: $rfq) {
    id
    cost
    deliveryDate
    carrier {
      id
      name
    }
  }
}
```

### LtlRfqInput Schema
```graphql
input LtlRfqInput {
  origin: RfqEndpointInput!
  destination: RfqEndpointInput!
  pickupDate: String!           # Format: "YYYY-MM-DD"
  items: [ItemInput!]!
}

input RfqEndpointInput {
  postalCode: String!
  addressType: ADDRESS_TYPE!    # RESIDENTIAL, BUSINESS, BUSINESS_W_DOCK
}

input ItemInput {
  quantity: Int!
  packaging: PACKAGING_TYPES!   # PALLET, CRATE, BOX, etc.
  sizeUoM: DISTANCE_UOM!        # in, cm
  length: Int!
  width: Int!
  height: Int!
  weightUoM: WEIGHT_UOM!        # lbs, kg
  weight: Int!
  freightClass: FREIGHT_CLASS!
  value: Float!
  itemCondition: ITEM_CONDITION # NEW, USED
  stackable: Boolean
  hazardous: Boolean
  description: String
  pieces: Int
  country: COUNTRY              # USA, CAN
}
```

## Enum Values

### ADDRESS_TYPE
- `RESIDENTIAL` - Home/residential address
- `BUSINESS` - Business without loading dock
- `BUSINESS_W_DOCK` - Business with loading dock

### PACKAGING_TYPES
- `PALLET` - Standard pallet (most common)
- `CRATE` - Wooden crate
- `BOX` - Cardboard box
- `BUNDLE` - Bundled items
- `DRUM` - Barrel/drum
- `ROLL` - Rolled material
- `BAGS` - Bagged items

### FREIGHT_CLASS
```
CLASS_50, CLASS_55, CLASS_60, CLASS_65, CLASS_70, 
CLASS_77_5, CLASS_85, CLASS_92_5, CLASS_100, CLASS_110, 
CLASS_125, CLASS_150, CLASS_175, CLASS_200, CLASS_250, 
CLASS_300, CLASS_400, CLASS_500
```

### DISTANCE_UOM
- `in` - Inches
- `cm` - Centimeters

### WEIGHT_UOM
- `lbs` - Pounds
- `kg` - Kilograms

### ITEM_CONDITION
- `NEW`
- `USED`

### COUNTRY
- `USA`
- `CAN`

## Example Quote Request

```json
{
  "query": "query { requestLTLQuote(rfq: { origin: { postalCode: \"19440\", addressType: BUSINESS_W_DOCK }, destination: { postalCode: \"30066\", addressType: BUSINESS_W_DOCK }, pickupDate: \"2026-01-26\", items: [{ quantity: 10, packaging: PALLET, sizeUoM: in, length: 48, width: 40, height: 48, weightUoM: lbs, weight: 15000, freightClass: CLASS_70, value: 5000, itemCondition: NEW, stackable: false, hazardous: false, description: \"Pork Lard in plastic pails\", pieces: 10, country: USA }] }) { id cost deliveryDate carrier { id name } } }"
}
```

## Prepare Order Mutation

After customer selects a quote, use this mutation to create the order:

```graphql
mutation {
  prepareOrder(input: {
    quoteId: "quote-id-from-requestLTLQuote"
    orderNumber: "your-order-number"
    origin: {
      address: {
        streetAddress: "1234 Main Street"
        postalCode: "12345"
        city: "City"
        state: "ST"
        country: USA
        firstName: "John"
        lastName: "Doe"
        companyName: "Company"
        phone: { areaCode: "888", countryCode: "1", number: "1234567" }
        email: "email@example.com"
      }
      startTime: "2026-01-26 08:00:00.000 -0500"
      endTime: "2026-01-26 17:00:00.000 -0500"
    }
    destination: {
      # Same structure as origin
    }
  }) {
    vendorOrder { id }
    error
  }
}
```

## Response Format

### Quote Response
```json
{
  "data": {
    "requestLTLQuote": [
      {
        "id": "283cdf9e-2e52-439b-b066-1eb4f594387e",
        "cost": 424.39,
        "deliveryDate": "2026-01-30",
        "carrier": {
          "id": "carrier-123",
          "name": "ABF Freight System, Inc."
        }
      }
    ]
  }
}
```

## Default Values

When not specified, use these defaults:
- `length`: 48 (standard pallet)
- `width`: 40 (standard pallet)
- `height`: 48 (standard pallet height)
- `sizeUoM`: in
- `weightUoM`: lbs
- `packaging`: PALLET
- `itemCondition`: NEW
- `stackable`: false
- `hazardous`: false
- `country`: USA
- `addressType`: BUSINESS_W_DOCK (for commercial shipments)
- `value`: Estimate 10-20% of shipment value or $100 per pallet minimum

## Error Handling

Common errors:
- Invalid API key: Check `X-GoShip-API-Key` header
- Invalid postal code: Ensure 5-digit US zip
- Past pickup date: Must be future date
- Missing required fields: Check all required inputs
