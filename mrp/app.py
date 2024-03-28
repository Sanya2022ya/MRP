from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
import json

app = Flask(__name__)


def db_conn():
    conn = psycopg2.connect(database="mrp", host="localhost", user="postgres", password="asdf56y", port="5432")
    return conn


@app.route('/')
def home():
    return render_template('layout.html')


# ---- Nodes CRUD Operations ----
@app.route('/nodes')
def nodes_index():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM nodes ORDER by id''')
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('nodes.html', data=data)


@app.route('/nodes/create', methods=['POST'])
def nodes_create():
    conn = db_conn()
    cur = conn.cursor()
    nodename = request.form['nodename']
    nodedescription = request.form['nodedescription']
    cur.execute('''INSERT INTO nodes (nodename, nodedescription) VALUES(%s, %s)''', (nodename, nodedescription))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('nodes_index'))


@app.route('/nodes/update', methods=['POST'])
def nodes_update():
    conn = db_conn()
    cur = conn.cursor()
    nodename = request.form['nodename']
    nodedescription = request.form['nodedescription']
    node_id = request.form['id']
    cur.execute('''UPDATE nodes SET nodename=%s, nodedescription=%s WHERE id=%s''', (nodename, nodedescription, node_id))
    conn.commit()
    return redirect(url_for('nodes_index'))


@app.route('/nodes/delete', methods=['POST'])
def nodes_delete():
    conn = db_conn()
    cur = conn.cursor()
    node_id = request.form['id']
    cur.execute('''DELETE FROM nodes WHERE id=%s''', (node_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('nodes_index'))

@app.route('/nodes/get', methods=['GET'])
def nodes_get():
    node_name = request.args.get('search', '')

    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM nodes WHERE nodename ILIKE %s''', ('%' + node_name + '%',))
    data = cur.fetchall()
    cur.close()
    conn.close()

    if not data:
        return render_template('nodes.html', data=data, error='Node with the specified name not found')

    return render_template('nodes.html', data=data)


# ---- Links CRUD Operations ----
@app.route('/links')
def links_index():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT l.id, 
                          l.upperNodeName, 
                          n1.nodeName AS upperNodeFullName, 
                          l.lowerNodeName, 
                          n2.nodeName AS lowerNodeFullName, 
                          l.weight, 
                          l.unitOfMeasurement 
                   FROM links l
                   INNER JOIN nodes n1 ON l.upperNodeName = n1.id
                   INNER JOIN nodes n2 ON l.lowerNodeName = n2.id
                   ORDER by l.id''')
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('links.html', data=data)


@app.route('/links/create', methods=['POST'])
def links_create():
    conn = db_conn()
    cur = conn.cursor()
    upper_node_id = request.form['upper_node_id']
    lower_node_id = request.form['lower_node_id']
    weight = request.form['weight']
    unit_of_measurement = request.form['unit_of_measurement']
    cur.execute(
        '''INSERT INTO links (upperNodeName, lowerNodeName, weight, unitOfMeasurement) 
           VALUES(%s, %s, %s, %s)''',
        (upper_node_id, lower_node_id, weight, unit_of_measurement)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('links_index'))


@app.route('/links/update', methods=['POST'])
def links_update():
    conn = db_conn()
    cur = conn.cursor()

    # Получаем значения из формы
    upper_node_full_name = request.form['upper_node_full_name']
    lower_node_full_name = request.form['lower_node_full_name']
    weight = request.form['weight']
    unit_of_measurement = request.form['unit_of_measurement']
    link_id = request.form['id']

    # Получаем идентификаторы узлов на основе их полных имен
    cur.execute('''SELECT id FROM nodes WHERE nodeName = %s''', (upper_node_full_name,))
    result = cur.fetchone()
    if result:
        upper_node_id = result[0]
    else:
        # Обработка случая, когда узел верхнего уровня не найден
        # Можно вернуть сообщение об ошибке или выполнить другие действия по вашему усмотрению
        # В данном случае я просто возвращаю пустой ответ
        return "Ошибка: Узел верхнего уровня не найден"

    cur.execute('''SELECT id FROM nodes WHERE nodeName = %s''', (lower_node_full_name,))
    result = cur.fetchone()
    if result:
        lower_node_id = result[0]
    else:
        # Обработка случая, когда узел нижнего уровня не найден
        # Можно вернуть сообщение об ошибке или выполнить другие действия по вашему усмотрению
        # В данном случае я просто возвращаю пустой ответ
        return "Ошибка: Узел нижнего уровня не найден"

    # Обновляем запись в базе данных с использованием идентификаторов узлов
    cur.execute(
        '''UPDATE links 
           SET upperNodeName = %s, lowerNodeName = %s, weight = %s, unitOfMeasurement = %s 
           WHERE id = %s''',
        (upper_node_id, lower_node_id, weight, unit_of_measurement, link_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('links_index'))


@app.route('/links/delete', methods=['POST'])
def links_delete():
    conn = db_conn()
    cur = conn.cursor()
    link_id = request.form['id']
    cur.execute('''DELETE FROM links WHERE id=%s''', (link_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('links_index'))


# ---- Links CRUD Operations ----
@app.route('/links/get', methods=['GET'])
def links_get():
    id = request.args.get('id', '')

    conn = db_conn()
    cur = conn.cursor()

    if id:
        cur.execute('''SELECT l.id, 
                              l.upperNodeName, 
                              n1.nodeName AS upperNodeFullName, 
                              l.lowerNodeName, 
                              n2.nodeName AS lowerNodeFullName, 
                              l.weight, 
                              l.unitOfMeasurement 
                       FROM links l
                       INNER JOIN nodes n1 ON l.upperNodeName = n1.id
                       INNER JOIN nodes n2 ON l.lowerNodeName = n2.id
                       WHERE l.id = %s''', (id,))
    else:
        cur.execute('''SELECT l.id, 
                              l.upperNodeName, 
                              n1.nodeName AS upperNodeFullName, 
                              l.lowerNodeName, 
                              n2.nodeName AS lowerNodeFullName, 
                              l.weight, 
                              l.unitOfMeasurement 
                       FROM links l
                       INNER JOIN nodes n1 ON l.upperNodeName = n1.id
                       INNER JOIN nodes n2 ON l.lowerNodeName = n2.id''')

    data = cur.fetchall()
    cur.close()
    conn.close()

    if not data:
        return render_template('links.html', error='No links found')

    return render_template('links.html', data=data)



# ---- Orders CRUD Operations ----
@app.route('/orders')
def orders_index():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM orders ORDER by id''')
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('orders.html', data=data)


@app.route('/orders/create', methods=['POST'])
def orders_create():
    conn = db_conn()
    cur = conn.cursor()
    node_id = request.form['node_id']
    order_date = request.form['order_date']
    quantity_ordered = request.form['quantity_ordered']
    description = request.form['description']
    supplier = request.form['supplier']
    price = request.form['price']
    cur.execute(
        '''INSERT INTO orders (nodeid, orderdate, quantityordered, description, supplier, price) 
           VALUES(%s, %s, %s, %s, %s, %s)''',
        (node_id, order_date, quantity_ordered, description, supplier, price)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('orders_index'))


@app.route('/orders/update', methods=['POST'])
def orders_update():
    conn = db_conn()
    cur = conn.cursor()
    node_id = request.form['node_id']
    order_date = request.form['order_date']
    quantity_ordered = request.form['quantity_ordered']
    description = request.form['description']
    supplier = request.form['supplier']
    price = request.form['price']
    order_id = request.form['id']
    cur.execute(
        '''UPDATE orders SET nodeid=%s, orderdate=%s, quantityordered=%s, description=%s, supplier=%s, price=%s 
           WHERE id=%s''',
        (node_id, order_date, quantity_ordered, description, supplier, price, order_id)
    )
    conn.commit()
    return redirect(url_for('orders_index'))


@app.route('/orders/delete', methods=['POST'])
def orders_delete():
    conn = db_conn()
    cur = conn.cursor()
    order_id = request.form['id']
    cur.execute('''DELETE FROM orders WHERE id=%s''', (order_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('orders_index'))


@app.route('/orders/get', methods=['GET'])
def orders_get():
    id = request.args.get('id', '')

    conn = db_conn()
    cur = conn.cursor()

    if id:
        cur.execute('''SELECT * FROM orders WHERE id = %s''', (id,))
    else:
        cur.execute('''SELECT * FROM orders''')

    data = cur.fetchall()
    cur.close()
    conn.close()

    if not data:
        return render_template('orders.html', error='No orders found')

    return render_template('orders.html', data=data)


@app.route('/warehouse')
def warehouse_index():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM warehouse ORDER BY id''')
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('warehouse.html', data=data)


@app.route('/warehouse/create', methods=['POST'])
def warehouse_create():
    conn = db_conn()
    cur = conn.cursor()
    node_id = request.form['node_id']
    received_quantity = request.form['received_quantity']
    shipped_quantity = request.form['shipped_quantity']
    date = request.form['date']
    cur.execute('''INSERT INTO warehouse (nodeId, receivedQuantity, shippedQuantity, date) VALUES(%s, %s, %s, %s)''',
                (node_id, received_quantity, shipped_quantity, date))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('warehouse_index'))


@app.route('/warehouse/update', methods=['POST'])
def warehouse_update():
    conn = db_conn()
    cur = conn.cursor()
    node_id = request.form['node_id']
    received_quantity = request.form['received_quantity']
    shipped_quantity = request.form['shipped_quantity']
    date = request.form['date']
    warehouse_id = request.form['id']
    cur.execute('''UPDATE warehouse SET nodeId=%s, receivedQuantity=%s, shippedQuantity=%s, date=%s WHERE id=%s''',
                (node_id, received_quantity, shipped_quantity, date, warehouse_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('warehouse_index'))


@app.route('/warehouse/delete', methods=['POST'])
def warehouse_delete():
    conn = db_conn()
    cur = conn.cursor()
    warehouse_id = request.form['id']
    cur.execute('''DELETE FROM warehouse WHERE id=%s''', (warehouse_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('warehouse_index'))


@app.route('/warehouse/get', methods=['GET'])
def warehouse_get():
    search = request.args.get('search', '')

    conn = db_conn()
    cur = conn.cursor()

    if search:
        cur.execute('''SELECT * FROM warehouse WHERE nodeId = %s''', (search,))
    else:
        cur.execute('''SELECT * FROM warehouse''')

    data = cur.fetchall()
    cur.close()
    conn.close()

    if not data:
        return render_template('warehouse.html', error='No warehouse found')

    return render_template('warehouse.html', data=data)



if __name__ == '__main__':
    app.run(debug=True)
