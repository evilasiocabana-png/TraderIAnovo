# MT5 Read-Only Contract

MT5 access is read-only in this project baseline.

Allowed provider methods:

- `get_status()`
- `get_symbols()`
- `get_latest_price(symbol)`

Forbidden methods and behaviors:

- `order_send`
- `send_order`
- `buy`
- `sell`
- `close_position`
- `modify_order`
- Any real broker order execution
- Any operational connection mode without a future approved mission

The test suite enforces these restrictions.
