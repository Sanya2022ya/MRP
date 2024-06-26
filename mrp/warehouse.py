from collections import defaultdict

from flask import render_template, request, redirect, url_for, Blueprint
import psycopg2

warehouse_bp = Blueprint('warehouse', __name__)


def db_conn():
    conn = psycopg2.connect(database="mrp", host="localhost", user="postgres", password="asdf56y", port="5432")
    return conn


@warehouse_bp.route('/warehouse')
def warehouse_index():
    conn = db_conn()
    cur = conn.cursor()

    # Выполняем JOIN запрос для получения данных из таблицы warehouse и nodes
    cur.execute('''
        SELECT w.id, w.nodeId, n.nodeName, w.receivedQuantity, w.shippedQuantity, w.date
        FROM warehouse w
        JOIN nodes n ON w.nodeId = n.id
        ORDER BY w.id
    ''')

    data = cur.fetchall()
    cur.close()
    conn.close()

    # Передаем данные в шаблон
    return render_template('warehouse.html', data=data)


@warehouse_bp.route('/warehouse/create', methods=['GET', 'POST'])
def warehouse_create():
    conn = db_conn()
    cur = conn.cursor()

    # Если метод POST, обработайте отправку формы
    if request.method == 'POST':
        node_id = request.form['node_id']
        received_quantity = request.form['received_quantity']
        shipped_quantity = request.form['shipped_quantity']
        date = request.form['date']

        # Выполните вставку нового склада в таблицу
        cur.execute('''INSERT INTO warehouse (nodeId, receivedQuantity, shippedQuantity, date)
                        VALUES (%s, %s, %s, %s)''',
                    (node_id, received_quantity, shipped_quantity, date))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('warehouse.warehouse_index'))

    # Если метод GET, получите список узлов и передайте его в шаблон
    cur.execute('''SELECT id, nodeName FROM nodes''')
    nodes = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('warehouse_create.html', nodes=nodes)


@warehouse_bp.route('/warehouse/update', methods=['POST'])
def warehouse_update():
    conn = db_conn()
    cur = conn.cursor()

    # Получаем данные из формы
    node_id = request.form['node_id']
    received_quantity = request.form['received_quantity']
    shipped_quantity = request.form['shipped_quantity']
    date = request.form['date']
    warehouse_id = request.form['id']

    # Извлекаем node_name на основе node_id
    cur.execute('SELECT nodeName FROM nodes WHERE id = %s', (node_id,))
    node_name_result = cur.fetchone()
    if node_name_result:
        node_name = node_name_result[0]  # Получаем значение node_name

        # Обновляем запись в таблице warehouse
        cur.execute('''
            UPDATE warehouse
            SET nodeId = %s, receivedQuantity = %s, shippedQuantity = %s, date = %s
            WHERE id = %s
        ''', (node_id, received_quantity, shipped_quantity, date, warehouse_id))

        # Сохраняем изменения
        conn.commit()

    # Закрываем соединение и курсор
    cur.close()
    conn.close()

    # Перенаправляем на страницу warehouse_index
    return redirect(url_for('warehouse.warehouse_index'))


@warehouse_bp.route('/warehouse/delete', methods=['POST'])
def warehouse_delete():
    conn = db_conn()
    cur = conn.cursor()
    warehouse_id = request.form['id']
    cur.execute('''DELETE FROM warehouse WHERE id=%s''', (warehouse_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('warehouse.warehouse_index'))


@warehouse_bp.route('/warehouse/get', methods=['GET'])
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

@warehouse_bp.route('/warehouse/details', methods=['GET'])
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
            return render_template('warehouse.html', lowest_nodes=all_lowest_nodes_list)

        except ValueError:
            # Обрабатываем ошибку в случае некорректной даты
            return "Ошибка: Некорректная дата"

    else:
        # Если дата не передана, отобразим страницу без данных
        return render_template('warehouse.html')




def get_node_ids_by_date(cursor, order_date):
    cursor.execute('''
        SELECT DISTINCT nodeId, SUM(receivedQuantity) - SUM(shippedQuantity) as quantity_ordered
        FROM Warehouse
        WHERE date <= %s
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



