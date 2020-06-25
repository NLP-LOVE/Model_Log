#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# @Time : 2020/6/10 10:04
# @Author : mantch
# @Version：V 1.0
# @desc : https://github.com/NLP-LOVE/Model_Log

from flask import Flask, request, jsonify, redirect, session
from flask import render_template
import webbrowser
import argparse
import signal
import sys
import os
import sqlite3
import pickle
from model_log.modellog import ModelLog

current_path = os.path.dirname(__file__)
app = Flask(__name__)
app.config["SECRET_KEY"] = "model_log"
page_size = 15


# 数据库连接
def get_conn():
    return sqlite3.connect(os.path.join(current_path, 'model_log.db'))


# 构造表头
def generate_table_head(conn, project_id):
    sql = "select sm.sub_model_id, sm.sub_model_name, sm.sub_model_remark, sm.create_time from sub_model sm where sm.project_id=%d and sm.del_flag=0" % (project_id)
    sub_model_result = conn.execute(sql).fetchall()

    # 构造表头
    table_head = {}
    table_length = {}
    sub_model_param = {}

    for sub_model in sub_model_result:

        sql = "select mp.param_type, mp.param_name, mp.param_value from model_param mp where mp.sub_model_id=%d" % (
        sub_model[0])
        model_param_result = conn.execute(sql)

        for model_param in model_param_result:

            # 添加 table head
            if model_param[0] not in table_head:
                table_head[model_param[0]] = [model_param[1]]
            else:
                if model_param[1] not in table_head[model_param[0]]:
                    table_head[model_param[0]].append(model_param[1])

            # sub_model_param
            if sub_model[0] not in sub_model_param:
                sub_model_param[sub_model[0]] = {model_param[1]: model_param[2]}
            else:
                sub_model_param[sub_model[0]][model_param[1]] = model_param[2]

    for type, param_list in table_head.items():
        table_length[type] = len(param_list)


    return sub_model_result, sub_model_param, table_head, table_length



# 构造页面数据
def generate_table_data(conn, table_head, sub_model_result, sub_model_param):
    table_data = []
    best_head = []
    best_data = {}
    first_param = {}
    modify_head = []
    id = 0
    for i, sub_model in enumerate(sub_model_result):

        # 评估指标数据
        sql = "select br.best_name, br.best_value from best_result br where br.sub_model_id=%d" % (sub_model[0])
        best_result = conn.execute(sql)
        dic = {}

        flag = False
        for best in best_result:
            if best[0] not in best_head:
                best_head.append(best[0])

            dic[best[0]] = best[1]
            flag = True

        best_data[sub_model[0]] = dic

        id += 1
        dic = {}

        dic['id'] = id
        dic['sub_model_id'] = sub_model[0]
        dic['sub_model_name'] = sub_model[1]
        dic['sub_model_remark'] = sub_model[2]
        dic['create_time'] = sub_model[3]

        if flag:
            dic['finished_train'] = True
        else:
            dic['finished_train'] = False

        # 超参数
        for _, param_list in table_head.items():
            for param_name in param_list:

                try:
                    dic[param_name] = sub_model_param[sub_model[0]][param_name]
                except:
                    dic[param_name] = ''

                if i == 0:  # 记录第一次训练的超参数
                    first_param[param_name] = dic[param_name]
                else:
                    if dic[param_name] != first_param[param_name]:
                        modify_head.append(param_name)

        # 评估指标数据
        for name in best_head:
            try:
                dic[name] = best_data[sub_model[0]][name]
            except:
                dic[name] = ''

        table_data.append(dic)


    return table_data, best_head, modify_head


# 构造loss画图数据
def generate_loss_data(conn, project_id, sub_model_result):
    sql = "select max(md.epoch) from model_metric md " \
          "left join sub_model sm on sm.sub_model_id=md.sub_model_id " \
          "left join project m on m.project_id = sm.project_id " \
          "where m.project_id=%d" % (project_id)
    max_step = conn.execute(sql).fetchall()[0][0]
    x_value = [i for i in range(1, max_step + 1)]

    legend = {}
    series = []
    for i, sub_model in enumerate(sub_model_result):

        if i + 1 == len(sub_model_result):
            legend[sub_model[1] + '_train'] = 'true'
            legend[sub_model[1] + '_test'] = 'true'
        else:
            legend[sub_model[1] + '_train'] = 'false'
            legend[sub_model[1] + '_test'] = 'false'

        sql = "select md.metric_value from model_metric md where md.sub_model_id=%d and md.metric_name='train_loss'" % (
        sub_model[0])
        train_value = [value[0] for value in conn.execute(sql)]
        data_dic = {'name': sub_model[1] + '_train', 'data': str(train_value)}
        series.append(data_dic)

        sql = "select md.metric_value from model_metric md where md.sub_model_id=%d and md.metric_name='test_loss'" % (
        sub_model[0])
        test_value = [value[0] for value in conn.execute(sql)]
        data_dic = {'name': sub_model[1] + '_test', 'data': str(test_value)}
        series.append(data_dic)

    x_value = str(x_value)

    return legend, x_value, series

def generate_new_loss(conn, sub_model_id, sub_model_name):

    sql = "select md.metric_value from model_metric md where md.sub_model_id=%d and md.metric_name='train_loss'" % (sub_model_id)
    train_value = [value[0] for value in conn.execute(sql)]

    sql = "select md.metric_value from model_metric md where md.sub_model_id=%d and md.metric_name='test_loss'" % (
        sub_model_id)
    test_value = [value[0] for value in conn.execute(sql)]

    data_list_loss = {'xAxis':{'data':[i for i in range(1, len(train_value) + 1)]},
                      'series':[{'name':sub_model_name + '_train', 'data':train_value},
                                {'name':sub_model_name + '_test', 'data':test_value}]}

    return data_list_loss


# 构造 acc画图数据
def generate_indicater_data(conn, sub_model_result, type):
    legend_acc = {}
    series_acc = []
    for i, sub_model in enumerate(sub_model_result):

        if i + 1 == len(sub_model_result):
            legend_acc[sub_model[1] + '_test'] = 'true'
        else:
            legend_acc[sub_model[1] + '_test'] = 'false'

        sql = "select md.metric_value from model_metric md where md.sub_model_id=%d and md.metric_name='%s'" % (
        sub_model[0], type)
        test_value = [value[0] for value in conn.execute(sql)]
        data_dic = {'name': sub_model[1] + '_test', 'data': str(test_value)}
        series_acc.append(data_dic)

    return legend_acc, series_acc

def generate_new_indicater_data(conn, sub_model_id, sub_model_name, type):

    sql = "select md.metric_value from model_metric md where md.sub_model_id=%d and md.metric_name='%s'" % (sub_model_id, type)
    value_list = [value[0] for value in conn.execute(sql)]

    data_dict = {'xAxis': {'data': [i for i in range(1, len(value_list) + 1)]},
                      'series': [{'name': sub_model_name + '_test', 'data': value_list}]}

    return data_dict

# 删除model
def delete_model(conn, project_id):
    sql = "delete from project where project_id=%d" % (project_id)
    conn.execute(sql)
    conn.commit()


def delete_sub_model(del_set):
    sql = "delete from sub_model where sub_model_id in %s" % (del_set)
    conn = get_conn()
    conn.execute(sql)

    sql = "delete from model_param where sub_model_id in %s" % (del_set)
    conn.execute(sql)

    sql = "delete from model_metric where sub_model_id in %s" % (del_set)
    conn.execute(sql)

    sql = "delete from best_result where sub_model_id in %s" % (del_set)
    conn.execute(sql)

    conn.commit()
    conn.close()

## 模型总数
def get_model_num(conn, nick_name):
    sql = "select count(1) from sub_model sm where sm.nick_name='%s'" % (nick_name)
    model_num = conn.execute(sql).fetchall()[0][0]
    return model_num

# 检查是否登录
def check_login(sess):

    if 'nick_name' not in session:
        return False
    elif session['nick_name'] == '':
        return False
    else:
        return True


# 进行初始化
def init_db(nick_name):

    for i in ['1','2']:
        with open(os.path.join(current_path, 'tf_param.pkl'), 'rb') as file:
            tf_param = pickle.load(file)
            if i == '1':
                tf_param['learning_rate'] = 0.001

        with open(os.path.join(current_path, 'metric_list' + i + '.pkl'), 'rb') as file:
            metric_list = pickle.load(file)

        model_log = ModelLog(nick_name, 'demo命名实体识别')
        model_log.add_model_name('BILSTM_CRF模型')
        model_log.add_param(tf_param, 'tf_param')

        for n, item in enumerate(metric_list):
            model_log.add_metric('train_loss', item['train_loss'], n + 1)
            model_log.add_metric('test_loss', item['test_loss'], n + 1)
            model_log.add_metric('test_acc', item['test_acc'], n + 1)
            model_log.add_metric('test_recall', item['test_recall'], n + 1)
            model_log.add_metric('test_precision', item['test_precision'], n + 1)
            model_log.add_metric('test_F1', item['test_F1'], n + 1)

        if i == '1':
            model_log.add_best_result('best_loss', 4.9491, 14)
            model_log.add_best_result('best_acc', 0.8937, 14)
            model_log.add_best_result('best_precision', 0.8315, 14)
            model_log.add_best_result('best_F1', 0.8615, 14)
            model_log.add_best_result('best_step', 14, 14)
        else:
            model_log.add_best_result('best_loss', 2.7031, 29)
            model_log.add_best_result('best_acc', 0.8937, 29)
            model_log.add_best_result('best_precision', 0.8285, 29)
            model_log.add_best_result('best_F1', 0.8598, 29)
            model_log.add_best_result('best_step', 29, 29)

        del model_log


@app.before_request
def check_platform():

    phone = ['android', 'iphone', 'ipad']

    platform = request.user_agent.platform
    platform = platform.lower()

    if platform in phone:
        return render_template('alert.html')




@app.route('/')
def to_index():

    conn = get_conn()
    model_num = 0

    is_login = check_login(session)

    '''
    if is_login:
        del session['nick_name']
        is_login = False
    '''

    nick_name = ''
    if is_login:
        nick_name = session['nick_name']
        model_num = get_model_num(conn, nick_name)

    conn.close()
    return render_template('index.html', model_num=model_num, is_login=is_login, nick_name=nick_name)

@app.route('/login', methods=['POST'])
def login():
    nick_name = request.get_json()['nick_name']

    session['nick_name'] = nick_name
    message = {}
    message['is_success'] = True

    ## 判断是否进行初始化数据
    conn = get_conn()
    sql = "select count(1) from project p where p.nick_name='%s'" % (nick_name)
    num = conn.execute(sql).fetchall()[0][0]

    if num == 0:
        init_db(nick_name)

    conn.close()
    return jsonify(message)



@app.route('/project_detail')
def project_detail():

    try:
        project_id = int(request.args.get('project_id'))
    except:
        raise Exception('project id 错误!')

    conn = get_conn()

    # 构造表头
    sub_model_result, sub_model_param, table_head, table_length = generate_table_head(conn, project_id)

    # 删除model
    if len(sub_model_result) == 0:
        delete_model(conn, project_id)

        conn.close()
        return redirect('/')

    # 构造页面数据
    table_data, best_head, modify_head = generate_table_data(conn, table_head, sub_model_result, sub_model_param)

    # 构造loss画图数据
    legend, x_value, series = generate_loss_data(conn, project_id, sub_model_result)

    # 构造 acc画图数据
    legend_acc, series_acc = generate_indicater_data(conn, sub_model_result, 'test_acc')

    # 构造recall画图数据
    legend_recall, series_recall = generate_indicater_data(conn, sub_model_result, 'test_recall')

    # 构造 precision画图数据
    legend_precision, series_precision = generate_indicater_data(conn, sub_model_result, 'test_precision')

    # 构造 F1画图数据
    legend_F1, series_F1 = generate_indicater_data(conn, sub_model_result, 'test_F1')

    # 模型个数
    if 'nick_name' not in session:
        return redirect('/')
    nick_name = session['nick_name']
    model_num = get_model_num(conn, nick_name)
    sub_model_num = len(sub_model_result)

    # 是否训练完成
    is_finished_train = table_data[-1]['finished_train']

    sql = "select p.project_name from project p where p.project_id=%d" % (project_id)
    project_name = conn.execute(sql).fetchall()[0][0]

    conn.close()
    return render_template('model_detail.html', table_head=table_head, table_data=table_data,
                           table_length=table_length, x_value=x_value, legend=legend, series=series,
                           legend_acc=legend_acc, series_acc=series_acc, best_head=best_head,
                           modify_head=modify_head, legend_precision=legend_precision,
                           series_precision=series_precision, legend_F1=legend_F1,
                           series_F1=series_F1, project_id=project_id, model_num=model_num,
                           sub_model_num=sub_model_num, is_finished_train=is_finished_train, nick_name=nick_name,
                           legend_recall=legend_recall, series_recall=series_recall, project_name=project_name)

# 动态获取最新数据
@app.route('/get_new_data', methods=['POST'])
def get_new_data():

    project_id = request.get_json()['project_id']
    message = {}
    conn = get_conn()


    try:


        sql = "select max(sm.sub_model_id), sm.sub_model_name from sub_model sm where sm.project_id=%d" % (project_id)
        sub_model_id = conn.execute(sql).fetchall()[0][0]
        sub_model_name = conn.execute(sql).fetchall()[0][1]

        # loss
        data_list_loss = generate_new_loss(conn, sub_model_id, sub_model_name)

        # acc
        data_list_acc = generate_new_indicater_data(conn, sub_model_id, sub_model_name, 'test_acc')

        # recall
        data_list_recall = generate_new_indicater_data(conn, sub_model_id, sub_model_name, 'test_recall')

        # precision
        data_list_precision = generate_new_indicater_data(conn, sub_model_id, sub_model_name, 'test_precision')

        # F1
        data_list_F1 = generate_new_indicater_data(conn, sub_model_id, sub_model_name, 'test_F1')

        # 判断是否训练完成
        sql = "select count(1) from best_result br where br.sub_model_id=%d" % (sub_model_id)
        best_count = conn.execute(sql).fetchall()[0][0]

        if best_count == 0:
            message['finished_train'] = False
        else:
            message['finished_train'] = True

        message['is_success'] = True
        message['data'] = {'loss': data_list_loss, 'acc': data_list_acc, 'recall': data_list_recall, 'precision': data_list_precision,
                           'F1': data_list_F1}


    except:
        message['is_success'] = False
        message['msg'] = '程序内部开小差啦！'

    conn.close()
    return jsonify(message)


# 检测是否有模型开始训练
@app.route('/check_new_model', methods=['POST'])
def check_new_model():

    model_num = request.get_json()['model_num']
    message = {}
    conn = get_conn()


    try:


        nick_name = session['nick_name']
        current_model_num = get_model_num(conn, nick_name)

        if model_num != current_model_num:
            sql = "select max(sm.sub_model_id), sm.project_id from sub_model sm"
            project_id = conn.execute(sql).fetchall()[0][1]
            message['is_jump'] = True
            message['project_id'] = project_id
        else:
            message['is_jump'] = False

        message['is_success'] = True



    except:
        message['is_success'] = False
        message['msg'] = '程序内部开小差啦！'

    conn.close()
    return jsonify(message)



# 删除model
@app.route('/del_project', methods=['POST'])
def del_model():
    del_list = request.get_json()['del_list']
    message = {}
    conn = get_conn()

    try:
        del_set = set()
        for id in del_list:
            del_set.add(int(id))

        del_set = str(del_set)
        del_set = del_set.replace('{', '(')
        del_set = del_set.replace('}', ')')


        sql = "select sm.sub_model_id from sub_model sm where sm.project_id in %s" % (del_set)
        sub_model_id_list = [id[0] for id in conn.execute(sql)]
        sub_model_id_list = str(sub_model_id_list)
        sub_model_id_list = sub_model_id_list.replace('[', '(')
        sub_model_id_list = sub_model_id_list.replace(']', ')')

        delete_sub_model(sub_model_id_list)

        # 删除model
        sql = "delete from project where project_id in %s" % (del_set)
        conn.execute(sql)

        conn.commit()
        message['is_success'] = True


    except Exception as e:
        message['is_success'] = False
        message['msg'] = '选中id错误！'
        print(e)

    conn.close()
    return jsonify(message)


@app.route('/del_sub_model', methods=['POST'])
def del_sub_model():

    del_list = request.get_json()['del_list']
    message = {}

    try:
        del_set = set()
        for id in del_list:
            del_set.add(int(id))

        del_set = str(del_set)
        del_set = del_set.replace('{', '(')
        del_set = del_set.replace('}', ')')

        delete_sub_model(del_set)

        message['is_success'] = True

    except Exception as e:
        message['is_success'] = False
        message['msg'] = '选中id错误！'
        print(e)


    return jsonify(message)

# db operation=================================================================


# 查询项目列表
@app.route('/get_project_list')
def get_project_list():

    try:
        page = int(request.args.get('page'))
    except:
        raise Exception('页码参数错误！')

    conn = get_conn()
    nick_name = session['nick_name']

    sql = "select m.project_name, m.project_remark, m.create_time, m.project_id from project m where m.del_flag = 0 and m.nick_name=? order by m.create_time desc limit ?,?"
    result = conn.execute(sql, (nick_name, (page - 1) * page_size, page_size))
    project_list = []

    id = (page - 1) * page_size
    for item in result:
        id += 1
        map_ = {'id':id, 'project_name':item[0], 'project_remark':item[1], 'create_time':item[2], 'project_id':item[3]}
        project_list.append(map_)

    conn.close()
    return jsonify(project_list)

# 查询项目总页数
@app.route('/get_page_num')
def get_page_num():

    if not check_login(session):
        return '-1'

    conn = get_conn()

    sql = "select count(1) from project m where m.del_flag = 0 and m.nick_name='%s'" % (session['nick_name'])
    result = conn.execute(sql).fetchall()[0][0]

    page_num = result / page_size

    if int(page_num) < page_num:
        page_num = int(page_num) + 1
    else:
        page_num = int(page_num)

    conn.close()
    return str(page_num)

@app.route('/alert')
def alert():
    return render_template('alert.html')


def my_exit(signum, frame):
    print()
    print('Good By!')
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, my_exit)
    signal.signal(signal.SIGTERM, my_exit)

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", type=int, default=5432, help="指定端口号")
    args = parser.parse_args()

    try:
        webbrowser.open('http://127.0.0.1:%d/' % (args.p))
        app.run(host='0.0.0.0', port=args.p)
    except Exception as e:
        print(str(args.p) + '端口已占用，请使用 model-log -p=5000 指定端口号，或关闭' + str(args.p) + '端口!')


if __name__ == '__main__':
    main()


