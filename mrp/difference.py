from flask import render_template, request, redirect, url_for, Blueprint
import psycopg2
from collections import defaultdict
difference_bp = Blueprint('difference', __name__)


def db_conn():
    conn = psycopg2.connect(database="mrp", host="localhost", user="postgres", password="asdf56y", port="5432")
    return conn


@difference_bp.route('/difference')
def difference_index_page():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM orders ORDER by id''')
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('difference.html', data=data)
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

@difference_bp.route('/difference/details', methods=['GET'])
def nodes_details_route():
    # Получаем дату из запроса
    order_date = request.args.get('order_date')

    if order_date:
        # Если передана дата, выполняем запрос к базе данных
        conn = db_conn()
        cur = conn.cursor()

        try:
            # Получаем номера узлов и соответствующее количество заказанного товара по дате
            node_ids_and_quantity_warehouse = get_node_ids_by_date_warehouse(cur, order_date)
            print(node_ids_and_quantity_warehouse)
            upper_nodes = []
            all_lowest_nodes = defaultdict(int)

            for node_id, quantity_ordered in node_ids_and_quantity_warehouse:
                details = nodes_details(node_id, cur, quantity_ordered)
                upper_nodes.append(details['upper_node'])
                for node in details['lowest_nodes']:
                    node_id, node_name, node_description, weight = node
                    all_lowest_nodes[(node_id, node_name, node_description)] += weight

            all_lowest_nodes_list_warehouse = [(node_id, node_name, node_description, weight) for (node_id, node_name, node_description), weight in all_lowest_nodes.items()]
            print(all_lowest_nodes_list_warehouse)

            # Получаем номера узлов и соответствующее количество заказанного товара по дате
            node_ids_and_quantity_orders = get_node_ids_by_date_orders(cur, order_date)
            print(node_ids_and_quantity_orders)
            upper_nodes = []
            all_lowest_nodes = defaultdict(int)

            for node_id, quantity_ordered in node_ids_and_quantity_orders:
                details = nodes_details(node_id, cur, quantity_ordered)
                upper_nodes.append(details['upper_node'])
                for node in details['lowest_nodes']:
                    node_id, node_name, node_description, weight = node
                    all_lowest_nodes[(node_id, node_name, node_description)] += weight

            all_lowest_nodes_list_orders = [(node_id, node_name, node_description, weight) for
                                     (node_id, node_name, node_description), weight in all_lowest_nodes.items()]
            print(all_lowest_nodes_list_orders)

            all_lowest_nodes_diff = {}

            for wh_node in all_lowest_nodes_list_warehouse:
                wh_node_id, _, _, wh_quantity = wh_node
                found_order_node = False

                for order_node in all_lowest_nodes_list_orders:
                    order_node_id, _, _, order_quantity = order_node

                    if wh_node_id == order_node_id:
                        diff_quantity = wh_quantity - order_quantity
                        all_lowest_nodes_diff[(wh_node_id, wh_node[1], wh_node[2])] = diff_quantity
                        found_order_node = True
                        break

                if not found_order_node:
                    all_lowest_nodes_diff[(wh_node_id, wh_node[1], wh_node[2])] = wh_quantity

            all_lowest_nodes_list = [(node_id, node_name, node_description, weight) for
                                     (node_id, node_name, node_description), weight in all_lowest_nodes_diff.items()]

            # Filter and invert negative values
            all_lowest_nodes_list_filtered = []

            for node in all_lowest_nodes_list:
                node_id, node_name, node_description, weight = node
                if weight < 0:
                    # Invert the weight since it's negative
                    weight = abs(weight)
                    all_lowest_nodes_list_filtered.append((node_id, node_name, node_description, weight))

            # Close the cursor and database connection
            cur.close()
            conn.close()

            # Return the results
            return render_template('difference.html', lowest_nodes=all_lowest_nodes_list_filtered)


        except ValueError:
            # Обрабатываем ошибку в случае некорректной даты
            return "Ошибка: Некорректная дата"

    else:
        # Если дата не передана, отобразим страницу без данных
        return render_template('difference.html')


def get_node_ids_by_date_warehouse(cursor, order_date):
    cursor.execute('''
        SELECT DISTINCT nodeId, SUM(receivedQuantity) - SUM(shippedQuantity) as quantity_ordered
        FROM Warehouse
        WHERE date <= %s
        GROUP BY nodeId
    ''', (order_date,))
    node_ids_and_quantity = cursor.fetchall()
    return node_ids_and_quantity


def get_node_ids_by_date_orders(cursor, order_date):
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

