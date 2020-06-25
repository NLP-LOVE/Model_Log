#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# @Time : 2020/6/10 10:04
# @Author : mantch
# @Version：V 1.0
# @desc : https://github.com/NLP-LOVE/Model_Log

import time
import sqlite3
import os
current_path = os.path.dirname(__file__)

def check_str(s, type):
    if not isinstance(s, str):
        raise Exception(type + ' not string!')
    elif s == '':
        raise Exception(type + ' is null!')

class ModelLog(object):

    """
    :param nick_name:        str，用户名，多人使用下可起到数据隔离。
    :param project_name:     str，项目名称。
    :param project_remark:   str，项目备注，默认为空。

    项目名称如不存在会新建
    """
    def __init__(self, nick_name, project_name, project_remark=''):

        self.conn = sqlite3.connect(os.path.join(current_path, 'model_log.db'))

        self.nick_name = nick_name
        self.project_name = project_name
        self.project_remark = project_remark
        self.start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.is_add_model_data = True
        self.param_dict = {}
        self.model_name = ''
        self.remark = ''

        check_str(project_name, 'project_name')
        check_str(nick_name, 'nick_name')


    # 检查project name 是否存在
    def __is_exist_project_name(self, project_name):

        sql = "select 1 from project m where m.project_name = '%s' and m.nick_name='%s'"%(project_name, self.nick_name)
        project_table = self.conn.execute(sql).fetchall()

        if len(project_table) != 0:
            return True
        else:
            return False

    # 检查model name 是否存在
    def __is_exist_model_name(self, model_name, project_id):

        sql = "select 1 from sub_model  sm where sm.project_id = %d and sm.sub_model_name = '%s'" % (project_id, model_name)
        project_table = self.conn.execute(sql).fetchall()

        if len(project_table) != 0:
            return True
        else:
            return False


    """
    :param param_dict: dict，训练参数字典
    :param param_type: str，参数类型，例如：TF参数、word2vec参数等。
    """
    def add_param(self, param_dict, param_type):

        check_str(param_type, 'param_type')

        self.param_dict[param_type] = param_dict

    """
    :param model_name: str，模型名称
    """
    def add_model_name(self, model_name):

        check_str(model_name, 'model_name')

        self.model_name = model_name

    """
    :param remark: str，模型备注
    """
    def add_model_remark(self, remark):

        check_str(remark, 'remark')

        self.remark = remark


    """
    :param metric_name:  str，评估指标名称，可选择['train_loss', 'test_loss', 'test_acc', 'test_recall', 'test_precision', 'test_F1']
    :param metric_value: float，评估指标数值。
    :param epoch:        int，训练周期

    第一次调用该 API 时，会把以上设置的数据持久化到 SQLite 数据库。
    可以在每个 epoch 周期的最后使用该 API添加训练集和测试集的评估指标，web端会自动获取该数据。
    """
    def add_metric(self, metric_name, metric_value, epoch):

        check_str(metric_name, 'metric_name')

        if metric_name not in ['train_loss', 'test_loss', 'test_acc', 'test_recall', 'test_precision', 'test_F1']:
            raise Exception("Your metric_name：%s, not in ['train_loss', 'test_loss', 'test_acc', 'test_recall', 'test_precision', 'test_F1']" % (metric_name))

        if self.is_add_model_data:
            self.__add_model_data()
            self.is_add_model_data = False

        create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        sql = "insert into model_metric values (null, ?, ?, 'line', ?, ?, ?)"
        self.conn.execute(sql, (self.sub_model_id, metric_name, epoch, '%.4f'%(metric_value), create_time))

        self.conn.commit()


    """
    :param best_name:  str，最佳评估指标名称，
    :param best_value: float，最佳评估指标数值。
    :param best_epoch: int，训练周期

    添加当前模型训练中最佳的评估数据，一般放到模型训练的最后进行添加。
    """
    def add_best_result(self, best_name, best_value, best_epoch):

        check_str(best_name, 'best_name')

        create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        sql = "insert into best_result values (null, ?, ?, ?, ?, ?)"
        self.conn.execute(sql, (self.sub_model_id, best_name, '%.4f' % (best_value), best_epoch, create_time))

        self.conn.commit()


    # 检查model_name是否重复
    def __check_model_name(self, model_name, sub_model_count, project_id):

        if model_name == '':
            model_name = self.project_name + '_' + str(sub_model_count + 1)

        else:

            # 判断是否有model_name
            if self.__is_exist_model_name(model_name, project_id):
                model_name = model_name + '_' + str(sub_model_count + 1)
            else:
                model_name = self.model_name

        if self.__is_exist_model_name(model_name, project_id):
            return self.__check_model_name(model_name, sub_model_count, project_id)
        else:
            return model_name


    # 添加模型数据
    def __add_model_data(self):

        # 插入model
        if not self.__is_exist_project_name(self.project_name):
            sql = "insert into project values (null, ?, ?, ?, ?, 0)"
            self.conn.execute(sql, (self.project_name, self.project_remark, self.nick_name, self.start_time))
            self.conn.commit()

        sql = "select project_id from project m where m.project_name = '%s' and m.nick_name='%s'"%(self.project_name, self.nick_name)
        project_id = self.conn.execute(sql).fetchall()[0][0]

        sql = "select count(1) from sub_model sm where sm.project_id = %d"%(project_id)
        sub_model_count = self.conn.execute(sql).fetchall()[0][0]

        # 插入sub model
        model_name = self.__check_model_name(self.model_name, sub_model_count, project_id)
        sql = "insert into sub_model values (null, ?, ?, ?, ?, ?, ?, 0)"
        self.conn.execute(sql, (project_id, sub_model_count + 1, model_name, self.remark, self.nick_name, self.start_time))
        self.conn.commit()

        sql = "select sub_model_id from sub_model sm where sm.project_id = ? and sm.sub_model_name = ?"
        self.sub_model_id = self.conn.execute(sql, (project_id, model_name)).fetchall()[0][0]

        # 插入model param
        for param_type, value in self.param_dict.items():

            for param_name, param_value in value.items():
                sql = "insert into model_param values (null, ?, ?, ?, ?, ?)"
                self.conn.execute(sql, (self.sub_model_id, param_type, param_name, str(param_value), self.start_time))

    # db数据库初始化
    def __init_db(self):

        sql_script = open(os.path.join(current_path, 'init_db.sql'), 'r', encoding='utf-8').read()

        self.conn.executescript(sql_script)

        self.conn.commit()

    """
    关闭 SQLite 数据库连接
    """
    def close(self):
        self.conn.close()


if __name__ == '__main__':



    model_log = ModelLog('test项目', 'test备注')
    '''
    # 训练参数
    tf_param = {}
    tf_param['model'] = 'BILSTM_Attention'
    tf_param['optimizer'] = 'adam'
    tf_param['num_classes'] = 10
    tf_param['lr'] = 0.001
    tf_param['training_steps'] = 1000000
    tf_param['display_step'] = 1
    tf_param['batch_size'] = 100
    tf_param['num_hidden'] = 128
    tf_param['embedding_dim'] = 128
    tf_param['drop_out'] = 0.5

    model_log.add_model_name('bilstm_crf')
    model_log.add_model_remark('bilstm_crf备注')
    model_log.add_param(tf_param, 'tf_param')

    for i in range(1, 21):
        model_log.add_diagram('train_loss', 25.0 - i, i)
        model_log.add_diagram('test_loss', 24.0 - i, i)
        model_log.add_diagram('test_acc', 0.3 + 0.02 * i, i)

    model_log.add_best_result('best_loss', 2.34, 20)
    model_log.add_best_result('best_acc', 0.99, 20)
    
    '''

    #model_log.init_db()







