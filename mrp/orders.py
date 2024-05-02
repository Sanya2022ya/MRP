from flask import render_template, request, redirect, url_for, Blueprint
import psycopg2
from collections import defaultdict
orders_bp = Blueprint('orders', __name__)


def db_conn():
    conn = psycopg2.connect(database="mrp", host="localhost", user="postgres", password="asdf56y", port="5432")
    return conn


@orders_bp.route('/orders')
def orders_index_page():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM orders ORDER by id''')
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('orders.html', data=data)


@orders_bp.route('/orders/create', methods=['POST'])
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
    return redirect(url_for('orders.orders_index_page'))


@orders_bp.route('/orders/update', methods=['POST'])
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
    return redirect(url_for('orders.orders_index_page'))


@orders_bp.route('/orders/delete', methods=['POST'])
def orders_delete():
    conn = db_conn()
    cur = conn.cursor()
    order_id = request.form['id']
    cur.execute('''DELETE FROM orders WHERE id=%s''', (order_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('orders.orders_index'))


@orders_bp.route('/orders/get', methods=['GET'])
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


def nodes_details(node_id, cur, quantity_ordered):
    try:
        # Запрос на получение информации о верхнем узле
        cur.execute('''SELECT * FROM nodes WHERE id = %s''', (node_id,))
        upper_node = cur.fetchone()

        # Получаем промежуточные и крайне низкие узлы для данного узла
        intermediate_nodes, lowest_nodes = get_intermediate_and_lowest_nodes(cur, node_id)

        # Вычисляем веса для промежуточных и крайне низких узлов
        for i, node in enumerate(intermediate_nodes):
            weight = quantity_ordered * node[3]  # Умножаем на quantityOrdered
            # Добавляем вес к информации об узлах
            intermediate_nodes[i] = node

        for i, node in enumerate(lowest_nodes):
            weight = quantity_ordered * node[3]
            updated_node = node[:3] + (weight,)  # Создаем новый кортеж с измененным значением веса
            lowest_nodes[i] = updated_node
            #print(updated_node[3])

        # Возвращаем результат в виде словаря
        return {
            'upper_node': upper_node,
            'intermediate_nodes': intermediate_nodes,
            'lowest_nodes': lowest_nodes
        }

    except ValueError:
        # Обрабатываем ошибку в случае некорректного node_id
        return None


from collections import defaultdict

@orders_bp.route('/orders/details', methods=['GET'])
def nodes_details_route():
    # Получаем дату из запроса
    order_date = request.args.get('order_date')

    if order_date:
        # Если передана дата, выполняем запрос к базе данных
        conn = db_conn()
        cur = conn.cursor()

        try:
            # Получаем номера узлов и соответствующее количество заказанного товара по дате
            node_ids_and_quantity = get_node_ids_by_date(cur, order_date)
            print(node_ids_and_quantity)
            upper_nodes = []
            all_lowest_nodes = defaultdict(int)

            for node_id, quantity_ordered in node_ids_and_quantity:
                details = nodes_details(node_id, cur, quantity_ordered)
                upper_nodes.append(details['upper_node'])
                for node in details['lowest_nodes']:
                    node_id, node_name, node_description, weight = node
                    all_lowest_nodes[(node_id, node_name, node_description)] += weight

            all_lowest_nodes_list = [(node_id, node_name, node_description, weight) for (node_id, node_name, node_description), weight in all_lowest_nodes.items()]
            print(all_lowest_nodes_list)
            # Закрываем курсор и подключение к базе данных
            cur.close()
            conn.close()

            # Возвращаем результаты
            return render_template('orders.html', lowest_nodes=all_lowest_nodes_list)

        except ValueError:
            # Обрабатываем ошибку в случае некорректной даты
            return "Ошибка: Некорректная дата"

    else:
        # Если дата не передана, отобразим страницу без данных
        return render_template('orders.html')


def get_node_ids_by_date(cursor, order_date):
    cursor.execute('''
        SELECT DISTINCT nodeId, SUM(quantityOrdered) as quantity_ordered
        FROM Orders
        WHERE orderDate <= %s
        GROUP BY nodeId
    ''', (order_date,))
    node_ids_and_quantity = cursor.fetchall()
    return node_ids_and_quantity


def compute_weight_for_node(cursor, upper_node_id, current_node_id):
    # Запрос для получения всех связей между верхним узлом и текущим узлом
    cursor.execute('''WITH RECURSIVE Path AS (
                        SELECT upperNodeName, lowerNodeName, weight
                        FROM links
                        WHERE upperNodeName = %s AND lowerNodeName = %s
                        UNION
                        SELECT l.upperNodeName, l.lowerNodeName, l.weight
                        FROM Path p
                        JOIN links l ON p.lowerNodeName = l.upperNodeName
                    )
                    SELECT weight FROM Path''', (upper_node_id, current_node_id))

    # Получаем все найденные строки
    rows = cursor.fetchall()
    total_weight = 1

    # Перемножаем веса по всем найденным связям
    for row in rows:
        total_weight *= row[0]

    return total_weight


def get_intermediate_and_lowest_nodes(cursor, node_id, current_weight=1, level=0):
    # Query to fetch the node's name and description
    cursor.execute('''
        SELECT nodeName, nodeDescription
        FROM nodes
        WHERE id = %s
    ''', (node_id,))

    node_name, node_description = cursor.fetchone()

    # Query to fetch lower nodes and their connections
    cursor.execute('''
        SELECT nodes.id, nodes.nodeName, nodes.nodeDescription, links.weight
        FROM nodes
        JOIN links ON nodes.id = links.lowerNodeName
        WHERE links.upperNodeName = %s
    ''', (node_id,))

    lower_nodes = cursor.fetchall()
    intermediate_nodes = []
    lowest_nodes = []

    if not lower_nodes:
        # If there are no lower nodes, the current node is considered a lowest node
        lowest_nodes.append((node_id, node_name, node_description, current_weight))
    else:
        # Process lower nodes
        for node in lower_nodes:
            lower_node_id, node_name, node_description, link_weight = node
            total_weight = current_weight * link_weight

            # Recursively get nodes for the current lower node
            inter_nodes, low_nodes = get_intermediate_and_lowest_nodes(
                cursor, lower_node_id, total_weight, level=level + 1
            )

            # If the current node has lower nodes, add it to the intermediate nodes
            if inter_nodes:
                intermediate_nodes.append((lower_node_id, node_name, node_description, total_weight))

            # Add found nodes to the lists
            intermediate_nodes.extend(inter_nodes)
            lowest_nodes.extend(low_nodes)

    return intermediate_nodes, lowest_nodes
