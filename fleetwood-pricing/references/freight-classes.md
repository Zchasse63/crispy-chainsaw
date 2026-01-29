# NMFC Freight Class Guide

Freight classes range from CLASS_50 (lowest cost, most dense) to CLASS_500 (highest cost, least dense).

## Quick Class Determination

Class is based on: **Density, Stowability, Handling, Liability**

### Density Formula
```
Density (PCF) = Weight (lbs) / Cubic Feet
Cubic Feet = (L × W × H in inches) / 1728
```

### Density-to-Class Table

| Density (PCF) | Class |
|---------------|-------|
| 50+ | CLASS_50 |
| 35-50 | CLASS_55 |
| 30-35 | CLASS_60 |
| 22.5-30 | CLASS_65 |
| 15-22.5 | CLASS_70 |
| 13.5-15 CLASS_77_5 |
| 12-13.5 | CLASS_85 |
| 10.5-12 | CLASS_92_5 |
| 9-10.5 | CLASS_100 |
| 8-9 | CLASS_110 |
| 7-8 | CLASS_125 |
| 6-7 | CLASS_150 |
| 5-6 | CLASS_175 |
| 4-5 | CLASS_200 |
| 3-4 | CLASS_250 |
| 2-3 | CLASS_300 |
| 1-2 | CLASS_400 |
| <1 | CLASS_500 |

## Common Food Products

### Frozen Products (FROZEN temp mode)
- **Frozen cooked poultry/chicken**: CLASS_70 to CLASS_85
- **Frozen meat products**: CLASS_65 to CLASS_85
- **Frozen prepared foods**: CLASS_70 to CLASS_100

### Refrigerated Products (REFRIGERATED temp mode)
- **Fresh produce**: CLASS_85 to CLASS_150
- **Dairy products**: CLASS_70 to CLASS_92_5
- **Fresh meat**: CLASS_65 to CLASS_85

### Dry/Ambient Products (DRY temp mode)
- **Lard/fats in containers**: CLASS_65 to CLASS_70
- **Canned goods**: CLASS_55 to CLASS_70
- **Dry packaged foods**: CLASS_70 to CLASS_100
- **Beverages**: CLASS_70 to CLASS_85
- **Flour/grain products**: CLASS_55 to CLASS_65

## User's Common Commodities

Based on typical shipments:

| Commodity | Suggested Class | Temp Mode |
|-----------|----------------|-----------|
| Pork lard in plastic pails | CLASS_65 or CLASS_70 | DRY |
| Frozen fully cooked chicken | CLASS_70 or CLASS_85 | FROZEN |
| Frozen prepared meats | CLASS_70 | FROZEN |

## GoShip API Enum Values

Valid freight class values for the API:
```
CLASS_50, CLASS_55, CLASS_60, CLASS_65, CLASS_70, 
CLASS_77_5, CLASS_85, CLASS_92_5, CLASS_100, CLASS_110, 
CLASS_125, CLASS_150, CLASS_175, CLASS_200, CLASS_250, 
CLASS_300, CLASS_400, CLASS_500
```

## When Uncertain

If commodity is ambiguous:
1. Calculate density if dimensions available
2. Default to CLASS_70 for general food products
3. Use CLASS_85 for lighter/bulkier items
4. Ask user for clarification if critical
