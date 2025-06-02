## Annotation Schema

### Top-Level Fields

- `image_id`: string — frame filename
- `caption`: string — free-text description
- `speed`: float — in MPH
- `steering`: float — angle in degrees
- `graph`: {nodes, edges}

### Node Format

```json
[
  "car<bb>408,332,583,429<bb>",
  {
    "obj_name": "car",
    "object_type": "Ego-Vehicle",
    "boxes": [408.0, 332.0, 583.0, 429.0],
    ...
  }
]
