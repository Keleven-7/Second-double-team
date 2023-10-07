from flask import Flask, render_template, request, jsonify
import random
import threading

app = Flask(__name__)

def is_valid(sudo, x, y, val):
    # 检查行冲突
    if val in sudo[y]:
        return False

    # 检查列冲突
    for i in range(9):
        if sudo[i][x] == val:
            return False

    # 检查宫格冲突
    subgrid_x = (x // 3) * 3
    subgrid_y = (y // 3) * 3
    for i in range(subgrid_y, subgrid_y + 3):
        for j in range(subgrid_x, subgrid_x + 3):
            if sudo[i][j] == val:
                return False

    return True

def fill_sudoku(lock):
    sudo = [[0] * 9 for _ in range(9)]  # 创建一个9x9的数独棋盘，所有数值初始化为0

    def fill_from(y, val):
        nonlocal sudo   # 声明sudo为外部变量，否则在嵌套函数内无法修改全局变量

        for x in random.sample(range(9), 9):  # 随机对列进行排序
            if sudo[y][x] == 0 and is_valid(sudo, x, y, val):  # 如果该位置没有填数字且填上val不冲突
                sudo[y][x] = val  # 填上val

                if y == 8:  # 如果已经填完最后一行
                    if val == 9:  # 如果val已经是9了，说明本数独创建成功
                        return True
                    else:
                        if fill_from(0, val + 1):  # 否则继续递归下一个val
                            return True
                else:  # 如果还没填满
                    if fill_from(y + 1, val):
                        return True

                sudo[y][x] = 0  # 回溯，恢复为空白

        return False

    lock.acquire()  # 获取锁，防止并发修改sudo
    if fill_from(0, 1):  # 从第0行开始，val的初始值为1
        result = [row[:] for row in sudo]  # 拷贝一份数独棋盘，避免其他操作对结果的影响
    else:
        result = None
    lock.release()  # 释放锁

    return result


def dig_holes(sudo, lock, hole_cnt):
    idx = list(range(81))
    random.shuffle(idx)

    for i in range(hole_cnt):
        x = idx[i] % 9
        y = idx[i] // 9
        lock.acquire()  # 获取锁
        sudo[y][x] = 0
        lock.release()  # 释放锁


def solve_sudoku(sudo, lock):
    def solve_from(y, x):
        nonlocal sudo

        if y == 9:  # 如果已经解完最后一个位置，则返回True
            return True

        if sudo[y][x] != 0:  # 如果该位置已经有数字，则递归下一个位置
            if x == 8:
                return solve_from(y + 1, 0)
            else:
                return solve_from(y, x + 1)
        else:
            subgrid_x = (x // 3) * 3
            subgrid_y = (y // 3) * 3
            for val in range(1, 10):
                if is_valid(sudo, x, y, val):
                    sudo[y][x] = val
                    if x == 8 and solve_from(y + 1, 0) or x != 8 and solve_from(y, x + 1):
                        return True
                    sudo[y][x] = 0

            return False

    lock.acquire()
    solve_from(0, 0)
    result = [row[:] for row in sudo]
    lock.release()

    return result

import json

@app.route('/generate')
def generate():
    lock = threading.Lock()
    sudo = fill_sudoku(lock)
    if sudo is not None:
        dig_holes(sudo, lock, 50)
        return jsonify({'sudoku': sudo})
    else:
        return jsonify({'error': 'Failed to generate sudoku'})


@app.route('/solve', methods=['POST'])
def solve():
    sudo = request.json['sudoku']
    lock = threading.Lock()
    result = solve_sudoku(sudo, lock)
    return jsonify({'sudoku': result})

@app.route('/')
def home():
    sudokus = []
    lock = threading.Lock()
    results = []
    threads = []
    count = 0  # 计数器

    def generate_sudoku(lock, result_list):
        nonlocal count  # 使用nonlocal声明count为外部变量

        sudo = fill_sudoku(lock)
        if sudo is not None:
            dig_holes(sudo, lock, 50)
            result_list.append(sudo)
            count += 1  # 每成功生成一个棋盘，计数器加1

    # 创建线程并启动
    for _ in range(9):
        t = threading.Thread(target=generate_sudoku, args=(lock, results))
        threads.append(t)
        t.start()

    # 等待线程完成
    for t in threads:
        t.join()

    return render_template('index.html', sudokus=results[:count])


@app.route('/compile', methods=['POST'])
def compile():
    code = request.form.get('code')  # 获取前端传递的代码
    # 在这里执行编译操作，可以使用eval或exec函数执行Python代码
    result = eval(code)  # 假设编译结果为执行结果

    return result


if __name__ == '__main__':
    app.run()