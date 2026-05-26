import http.server
import json
import sqlite3
import os
import urllib.parse
import datetime
import random

DB_FILE = 'database.db'

# ==================== DATABASE INITIALIZATION ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create Menu table
    c.execute('''CREATE TABLE IF NOT EXISTS menu (
        id TEXT PRIMARY KEY,
        category TEXT,
        name TEXT,
        price REAL
    )''')
    
    # Create Customers table
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        number TEXT PRIMARY KEY,
        name TEXT,
        address TEXT,
        gstin TEXT,
        dob TEXT,
        anniversary TEXT
    )''')
    
    # Create Orders table (Completed/Pending POS transactions)
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        orderId TEXT PRIMARY KEY,
        dateTime TEXT,
        tableNo TEXT,
        rider TEXT,
        customer TEXT,
        status TEXT,
        amount REAL,
        discount REAL,
        gst REAL,
        charges REAL,
        paidAmount REAL,
        paymentMode TEXT,
        cart_json TEXT
    )''')
    
    # Create Tables state table (to persist active KOTs)
    c.execute('''CREATE TABLE IF NOT EXISTS tables_state (
        id TEXT PRIMARY KEY,
        number INTEGER,
        name TEXT,
        area TEXT,
        status TEXT,
        timer INTEGER,
        cart_json TEXT,
        customer_json TEXT,
        givenAmount REAL,
        tipAmount REAL,
        paymentMode TEXT,
        paymentRemark TEXT,
        invoiceNo TEXT,
        dateTime TEXT
    )''')
    
    # Create Online Aggregator Orders table
    c.execute('''CREATE TABLE IF NOT EXISTS online_orders (
        orderId TEXT PRIMARY KEY,
        placedAt TEXT,
        deliveryTime TEXT,
        channelName TEXT,
        orderStatus TEXT,
        cart_json TEXT
    )''')
    
    # Create Settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    conn.commit()

    # Pre-populate settings if empty
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO settings VALUES (?, ?)", ('auto_accept_online_orders', '0'))
        conn.commit()

    # Pre-populate menu if empty
    c.execute("SELECT COUNT(*) FROM menu")
    if c.fetchone()[0] == 0:
        default_menu = {
            'Burger and Sandwich': [
                ('bs-1', 'bbq burger', 159),
                ('bs-2', 'Aalo jeera (half)', 350),
                ('bs-3', 'Aalo jeera Full', 450),
                ('bs-4', 'Aalo Paratha+curd', 185),
                ('bs-5', 'Add On Caramelized Banana', 80),
                ('bs-6', 'Add On chicken', 50),
                ('bs-7', 'Afgani Chicken Tikka (Sai)', 0),
                ('bs-8', 'Appam (Vellayappam))', 36),
                ('bs-9', 'Appam(Vellayappam) Single)', 12),
                ('bs-10', 'apple juice', 60),
                ('bs-11', 'Ayala Curry', 200),
                ('bs-12', 'Ayala Fry', 130),
                ('bs-13', 'Baby corn Manchurian', 150)
            ],
            'Wraps & Pasta': [
                ('wp-1', 'Veg Wrap', 120),
                ('wp-2', 'Chicken Wrap', 149),
                ('wp-3', 'Alfredo White Pasta', 220),
                ('wp-4', 'Arrabbiata Red Pasta', 199)
            ],
            'Fried Chicken': [
                ('fc-1', 'Crispy Wings (4pcs)', 180),
                ('fc-2', 'Boleness strip 2', 79),
                ('fc-3', 'Fried Leg Piece', 99),
                ('fc-4', 'Bucket Chicken', 499)
            ],
            'Pizza': [
                ('pz-1', 'bbq pizza', 300),
                ('pz-2', 'bbq pizza 2', 0),
                ('pz-3', 'cheese burst pizza', 299),
                ('pz-4', 'cheese pizza', 300),
                ('pz-5', 'cheeze pizza (regular)', 300),
                ('pz-6', 'chicken & spicy pizza', 249),
                ('pz-7', 'digi pizza', 300),
                ('pz-8', 'margherita', 10),
                ('pz-9', 'margherita Pizza', 0),
                ('pz-10', 'margita pizza', 179),
                ('pz-11', 'mozza mexican masala', 355),
                ('pz-12', 'mushroom pizza', 0)
            ],
            'Egg Items & Fries': [
                ('ef-1', 'French Fries Large', 120),
                ('ef-2', 'Peri Peri Fries', 140),
                ('ef-3', 'Egg Omelette Single', 50),
                ('ef-4', 'Double Egg Roll', 90)
            ],
            'Beverages': [
                ('bv-1', 'Biriyani Rice', 80),
                ('bv-2', 'Cold Drink Can', 40),
                ('bv-3', 'Mineral Water', 20),
                ('bv-4', 'Fresh Lime Soda', 60)
            ]
        }
        for cat, items in default_menu.items():
            for item in items:
                c.execute("INSERT INTO menu (id, category, name, price) VALUES (?, ?, ?, ?)", (item[0], cat, item[1], item[2]))
        conn.commit()

    # Pre-populate customers if empty
    c.execute("SELECT COUNT(*) FROM customers")
    if c.fetchone()[0] == 0:
        default_customers = [
            ('7798908046', 'Vinayak', 'pune', '27AAAAA1111A1Z1', '1995-04-12', '2021-11-20'),
            ('9876543210', 'Rohan', 'Baner, Pune', '', '', ''),
            ('8888888888', 'Aditya', 'Kothrud, Pune', '', '', '')
        ]
        for cust in default_customers:
            c.execute("INSERT INTO customers (number, name, address, gstin, dob, anniversary) VALUES (?, ?, ?, ?, ?, ?)", cust)
        conn.commit()

    # Pre-populate initial tables state if empty
    c.execute("SELECT COUNT(*) FROM tables_state")
    if c.fetchone()[0] == 0:
        areas = ['ground', 'floor', 'vip', 'garden', 'ac', 'bar', 'testab']
        for area in areas:
            for i in range(1, 19):
                table_id = f"{area}-{i}"
                name = f"Table-{i}"
                # Initialize Ground-3 as active busy/billed to match screenshots
                if area == 'ground' and i == 3:
                    cart = [
                        { "item": { "id": "bs-1", "name": "bbq burger", "price": 159 }, "qty": 1, "remark": "" },
                        { "item": { "id": "fc-2", "name": "Boleness strip 2", "price": 79 }, "qty": 3, "remark": "" },
                        { "item": { "id": "bv-1", "name": "Biriyani Rice", "price": 80 }, "qty": 1, "remark": "" },
                        { "item": { "id": "pz-8", "name": "margherita", "price": 299 }, "qty": 1, "remark": "To Add : 10 inch,onion" }
                    ]
                    cust = { "name": "Vinayak", "number": "7798908046", "address": "pune", "gstin": "27AAAAA1111A1Z1", "dob": "1995-04-12", "anniversary": "2021-11-20" }
                    c.execute("""INSERT INTO tables_state 
                        (id, number, name, area, status, timer, cart_json, customer_json, givenAmount, tipAmount, paymentMode, paymentRemark, invoiceNo, dateTime) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                        (table_id, i, name, area, 'billed', 384, json.dumps(cart), json.dumps(cust), 802.0, 0.0, 'cash', '', 'TDO-R12812', '22-12-2022 15:09:13'))
                else:
                    empty_cust = { "name": "", "number": "", "address": "", "gstin": "", "dob": "", "anniversary": "" }
                    c.execute("""INSERT INTO tables_state 
                        (id, number, name, area, status, timer, cart_json, customer_json, givenAmount, tipAmount, paymentMode, paymentRemark, invoiceNo, dateTime) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                        (table_id, i, name, area, 'available', 0, '[]', json.dumps(empty_cust), 0.0, 0.0, 'cash', '', '', ''))
        conn.commit()

    # Pre-populate orders if empty (Initial completed order count = 105, revenue = 105729, etc. to match dashboard)
    c.execute("SELECT COUNT(*) FROM orders")
    if c.fetchone()[0] == 0:
        # Prepopulate with 2 open pending orders as seen in table list
        pending_orders = [
            ('TDO-R12813', '2022-12-22 15:08:09', 'Table-3', '--', '--', 'pending', 560.00, 0.0, 25.50, 0.00, 585.50, 'cash', '[]'),
            ('TDO-R12814', '2022-12-22 15:09:48', 'Take Away', '--', '--', 'pending', 327.00, 0.0, 16.35, 0.00, 343.35, 'cash', '[]')
        ]
        for o in pending_orders:
            c.execute("""INSERT INTO orders 
                (orderId, dateTime, tableNo, rider, customer, status, amount, discount, gst, charges, paidAmount, paymentMode, cart_json) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", o)
        
        # Inject standard historical completed orders to match dashboard values:
        # 103 completed orders, total revenue ~ 104800 (plus pending orders = 105 total, 105729 revenue)
        # Let's add aggregated orders to match cash (902) vs Paytm (209) proportions, or we can mock it directly.
        c.execute("""INSERT INTO orders 
            (orderId, dateTime, tableNo, rider, customer, status, amount, discount, gst, charges, paidAmount, paymentMode, cart_json) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ('TDO-R12810', '2022-12-22 14:30:00', 'Table-1', '--', 'Rohan', 'completed', 902.00, 0.0, 0.0, 0.0, 902.00, 'cash', '[]'))
        
        c.execute("""INSERT INTO orders 
            (orderId, dateTime, tableNo, rider, customer, status, amount, discount, gst, charges, paidAmount, paymentMode, cart_json) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ('TDO-R12811', '2022-12-22 14:45:00', 'Table-5', '--', 'Aditya', 'completed', 209.00, 0.0, 0.0, 0.0, 209.00, 'paytm', '[]'))
        
        # Add a placeholder large amount to match the dashboard's 105,729.00 revenue
        c.execute("""INSERT INTO orders 
            (orderId, dateTime, tableNo, rider, customer, status, amount, discount, gst, charges, paidAmount, paymentMode, cart_json) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ('TDO-R10000', '2022-12-01 12:00:00', 'Bulk Event', '--', 'Corporate', 'completed', 104618.00, 0.0, 0.0, 0.0, 104618.00, 'cash', '[]'))
            
        conn.commit()

    # Pre-populate online aggregator orders
    c.execute("SELECT COUNT(*) FROM online_orders")
    if c.fetchone()[0] == 0:
        default_online = [
            ('ONL-9981', '2022-12-22 15:01', '15:30', 'Swiggy', 'PLACED', json.dumps([
                { "item": { "name": "bbq burger", "price": 159 }, "qty": 2, "remark": "Extra cheese" }
            ])),
            ('ONL-9982', '2022-12-22 15:05', '15:40', 'Zomato', 'IN', json.dumps([
                { "item": { "name": "cheese burst pizza", "price": 299 }, "qty": 1, "remark": "" }
            ])),
            ('ONL-9983', '2022-12-22 14:50', '15:20', 'Swiggy', 'COMPLETED', json.dumps([
                { "item": { "name": "French Fries Large", "price": 120 }, "qty": 1, "remark": "" }
            ]))
        ]
        for oo in default_online:
            c.execute("INSERT INTO online_orders (orderId, placedAt, deliveryTime, channelName, orderStatus, cart_json) VALUES (?, ?, ?, ?, ?, ?)", oo)
        conn.commit()

    conn.close()

# ==================== REQUEST HANDLER ====================
class POSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS support for easier API testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # Parse API routes
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith('/api/'):
            self.handle_api_get(path, urllib.parse.parse_qs(parsed_url.query))
        else:
            # Fall back to serving static frontend files
            super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith('/api/'):
            # Parse post body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
            
            self.handle_api_post(path, data)
        else:
            self.send_response(404)
            self.end_headers()

    # ==================== GET ENDPOINTS ====================
    def handle_api_get(self, path, query_params):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        try:
            # 1. GET Tables State
            if path == '/api/tables':
                c.execute("SELECT * FROM tables_state")
                rows = c.fetchall()
                tables_dict = {}
                for r in rows:
                    tables_dict[r['id']] = {
                        'id': r['id'],
                        'number': r['number'],
                        'name': r['name'],
                        'area': r['area'],
                        'status': r['status'],
                        'timer': r['timer'],
                        'cart': json.loads(r['cart_json']),
                        'customer': json.loads(r['customer_json']),
                        'givenAmount': r['givenAmount'],
                        'tipAmount': r['tipAmount'],
                        'paymentMode': r['paymentMode'],
                        'paymentRemark': r['paymentRemark'],
                        'invoiceNo': r['invoiceNo'],
                        'dateTime': r['dateTime']
                    }
                self.send_json_response(200, tables_dict)

            # 2. GET Menu
            elif path == '/api/menu':
                c.execute("SELECT * FROM menu")
                rows = c.fetchall()
                menu_dict = {}
                for r in rows:
                    cat = r['category']
                    if cat not in menu_dict:
                        menu_dict[cat] = []
                    menu_dict[cat].append({
                        'id': r['id'],
                        'name': r['name'],
                        'price': r['price']
                    })
                self.send_json_response(200, menu_dict)

            # 3. GET Customers
            elif path == '/api/customers':
                c.execute("SELECT * FROM customers")
                rows = c.fetchall()
                customers_list = [dict(r) for r in rows]
                self.send_json_response(200, customers_list)

            # 4. GET Orders list
            elif path == '/api/orders':
                c.execute("SELECT * FROM orders")
                rows = c.fetchall()
                orders_list = []
                for r in rows:
                    orders_list.append({
                        'orderId': r['orderId'],
                        'dateTime': r['dateTime'],
                        'tableNo': r['tableNo'],
                        'rider': r['rider'],
                        'customer': r['customer'],
                        'status': r['status'],
                        'amount': r['amount'],
                        'discount': r['discount'],
                        'gst': r['gst'],
                        'charges': r['charges'],
                        'paidAmount': r['paidAmount'],
                        'paymentMode': r['paymentMode'],
                        'cart': json.loads(r['cart_json'])
                    })
                self.send_json_response(200, orders_list)

            # 5. GET Online Aggregator Orders
            elif path == '/api/online-orders':
                c.execute("SELECT * FROM online_orders")
                rows = c.fetchall()
                online_list = []
                for r in rows:
                    online_list.append({
                        'orderId': r['orderId'],
                        'placedAt': r['placedAt'],
                        'deliveryTime': r['deliveryTime'],
                        'channelName': r['channelName'],
                        'orderStatus': r['orderStatus'],
                        'cart': json.loads(r['cart_json'])
                    })
                
                # Fetch settings for auto accept
                c.execute("SELECT value FROM settings WHERE key='auto_accept_online_orders'")
                auto_accept = c.fetchone()['value'] == '1'

                self.send_json_response(200, {
                    'orders': online_list,
                    'autoAccept': auto_accept
                })

            # 6. GET Dashboard Stats
            elif path == '/api/dashboard':
                # Dynamically calculate numbers from SQLite orders
                c.execute("SELECT COUNT(*) FROM orders")
                total_placed = c.fetchone()[0]

                # Revenue sum of all completed orders
                c.execute("SELECT SUM(paidAmount) FROM orders WHERE status='completed'")
                revenue = c.fetchone()[0] or 0.0

                # Static lent amount (from screenshots: ₹687)
                lent_amount = 687.00
                feedback = 0

                # Calculate payment mode breakdown dynamically
                c.execute("SELECT paymentMode, SUM(paidAmount) as total FROM orders WHERE status='completed' GROUP BY paymentMode")
                payment_rows = c.fetchall()
                breakdown = {}
                for r in payment_rows:
                    if r['paymentMode']:
                        breakdown[r['paymentMode']] = round(r['total'])

                self.send_json_response(200, {
                    'ordersPlaced': total_placed,
                    'revenue': round(revenue),
                    'lentAmount': lent_amount,
                    'feedback': feedback,
                    'paymentBreakdown': breakdown
                })

            else:
                self.send_json_response(404, {'error': 'API Endpoint not found'})

        except Exception as e:
            self.send_json_response(500, {'error': str(e)})
        finally:
            conn.close()

    # ==================== POST ENDPOINTS ====================
    def handle_api_post(self, path, data):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        try:
            # 1. POST Update Table State
            if path == '/api/tables/update':
                t_id = data.get('id')
                status = data.get('status')
                timer = data.get('timer', 0)
                cart = data.get('cart', [])
                customer = data.get('customer', {})
                given_amount = data.get('givenAmount', 0.0)
                tip_amount = data.get('tipAmount', 0.0)
                payment_mode = data.get('paymentMode', 'cash')
                payment_remark = data.get('paymentRemark', '')
                invoice_no = data.get('invoiceNo', '')
                date_time = data.get('dateTime', '')

                c.execute("""UPDATE tables_state SET
                    status=?, timer=?, cart_json=?, customer_json=?, givenAmount=?, 
                    tipAmount=?, paymentMode=?, paymentRemark=?, invoiceNo=?, dateTime=?
                    WHERE id=?""",
                    (status, timer, json.dumps(cart), json.dumps(customer), given_amount,
                     tip_amount, payment_mode, payment_remark, invoice_no, date_time, t_id))
                conn.commit()
                self.send_json_response(200, {'success': True})

            # 2. POST Reset Table
            elif path == '/api/tables/reset':
                t_id = data.get('id')
                empty_cust = { "name": "", "number": "", "address": "", "gstin": "", "dob": "", "anniversary": "" }
                c.execute("""UPDATE tables_state SET
                    status='available', timer=0, cart_json='[]', customer_json=?, 
                    givenAmount=0.0, tipAmount=0.0, paymentMode='cash', paymentRemark='', invoiceNo='', dateTime=''
                    WHERE id=?""", (json.dumps(empty_cust), t_id))
                conn.commit()
                self.send_json_response(200, {'success': True})

            # 3. POST Save Transaction Order (completed or pending)
            elif path == '/api/orders/create':
                order_id = data.get('orderId')
                date_time = data.get('dateTime')
                table_no = data.get('tableNo')
                rider = data.get('rider', '--')
                customer = data.get('customer', '--')
                status = data.get('status', 'completed')
                amount = data.get('amount', 0.0)
                discount = data.get('discount', 0.0)
                gst = data.get('gst', 0.0)
                charges = data.get('charges', 0.0)
                paid_amount = data.get('paidAmount', 0.0)
                payment_mode = data.get('paymentMode', 'cash')
                cart = data.get('cart', [])

                c.execute("""INSERT OR REPLACE INTO orders 
                    (orderId, dateTime, tableNo, rider, customer, status, amount, discount, gst, charges, paidAmount, paymentMode, cart_json) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (order_id, date_time, table_no, rider, customer, status, amount, discount, gst, charges, paid_amount, payment_mode, json.dumps(cart)))
                conn.commit()
                self.send_json_response(200, {'success': True})

            # 4. POST Add Customer
            elif path == '/api/customers/add':
                number = data.get('number')
                name = data.get('name')
                address = data.get('address', '')
                gstin = data.get('gstin', '')
                dob = data.get('dob', '')
                anniversary = data.get('anniversary', '')

                c.execute("""INSERT OR REPLACE INTO customers 
                    (number, name, address, gstin, dob, anniversary) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (number, name, address, gstin, dob, anniversary))
                conn.commit()
                self.send_json_response(200, {'success': True})

            # 5. POST Toggle Auto Accept Aggregator Orders
            elif path == '/api/online-orders/toggle-auto-accept':
                val = '1' if data.get('enabled') else '0'
                c.execute("UPDATE settings SET value=? WHERE key='auto_accept_online_orders'", (val,))
                conn.commit()
                self.send_json_response(200, {'success': True})

            # 6. POST Update Online Order Status
            elif path == '/api/online-orders/update-status':
                order_id = data.get('orderId')
                new_status = data.get('status')
                c.execute("UPDATE online_orders SET orderStatus=? WHERE orderId=?", (new_status, order_id))
                conn.commit()
                self.send_json_response(200, {'success': True})

            # 7. POST Sync Aggregator Orders (mock generator)
            elif path == '/api/online-orders/sync':
                # Create a random new online order from Swiggy/Zomato
                new_id = f"ONL-{random.randint(1000, 9999)}"
                placed_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                deliv_time = (datetime.datetime.now() + datetime.timedelta(minutes=30)).strftime("%H:%M")
                channel = random.choice(['Swiggy', 'Zomato', 'Magicpin'])
                
                # Fetch random items from menu
                c.execute("SELECT id, name, price FROM menu ORDER BY RANDOM() LIMIT 2")
                items = c.fetchall()
                cart = []
                for item in items:
                    cart.append({
                        "item": { "id": item[0], "name": item[1], "price": item[2] },
                        "qty": random.randint(1, 3),
                        "remark": random.choice(["", "Less Spicy", "No Onion", "Extra cheese"])
                    })

                # Check if auto-accept is enabled
                c.execute("SELECT value FROM settings WHERE key='auto_accept_online_orders'")
                auto_accept = c.fetchone()[0] == '1'
                status = 'IN' if auto_accept else 'PLACED'

                c.execute("""INSERT INTO online_orders 
                    (orderId, placedAt, deliveryTime, channelName, orderStatus, cart_json) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (new_id, placed_time, deliv_time, channel, status, json.dumps(cart)))
                conn.commit()
                self.send_json_response(200, {'success': True, 'orderId': new_id, 'autoAccepted': auto_accept})

            else:
                self.send_json_response(404, {'error': 'API Endpoint not found'})

        except Exception as e:
            self.send_json_response(500, {'error': str(e)})
        finally:
            conn.close()

    # ==================== HELPERS ====================
    def send_json_response(self, code, obj):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        response_bytes = json.dumps(obj).encode('utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

# ==================== MAIN SERVER ====================
def run(port=8000):
    init_db()
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, POSRequestHandler)
    print(f"Starting server on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    print("Stopping server.")

if __name__ == '__main__':
    run()
