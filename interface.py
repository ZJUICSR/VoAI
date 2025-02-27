#!/usr/bin/env python
# -*- coding:utf-8 -*-

__copyright__ = 'Copyright © 2021/11/01, ZJUICSR'

import os, json, copy, torch, cv2
import os.path as osp
import torchvision
import time
from IOtool import IOtool, Callback
from torchvision import  transforms
from function.formal_verify import *
from function.formal_verify.knowledge_consistency import Model_zoo as zoomodels
from PIL import Image
from model.model_net.lenet import Lenet
import textattack
from function.attack import run_adversarial, run_backdoor
from function.fairness import run_dataset_debias, run_model_debias, run_image_model_debias, run_model_evaluate, run_image_model_evaluate
from function import concolic, env_test, coverage, deepsst, dataclean, framework_test, modelmeasure, modulardevelop, robust_gnn, adv_traind

from function.ex_methods import *
import matplotlib.pyplot as plt
from function.defense import *
from torchvision.models import vgg16
from torchvision.datasets import CIFAR10, mnist
from function.side import *
from scipy.stats import kendalltau
ROOT = osp.dirname(osp.abspath(__file__))
def run_model_debias_api(tid, stid, dataname, modelname, algorithmname, metrics = [], sensattrs = [], targetattr=None, staAttrList= [], 
                         test_mode = True, model_path='', save_folder=''):
    """模型公平性提升
    :params tid:主任务ID
    :params stid:子任务id
    :params dataname:数据集名称
    :params modelname:模型名称
    :params algorithmname:优化算法名称
    """
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    logging = IOtool.get_logger(stid)
    if dataname in ["Compas", "Adult", "German"]:
        res = run_model_debias(dataname, modelname, algorithmname, metrics, sensattrs, targetattr, staAttrList, logging=logging, model_path=model_path, save_folder=save_folder)
    else:
        res = run_image_model_debias(dataset_name=dataname,model_path=model_path, 
                                     model_name=modelname, algorithm_name=algorithmname, 
                                     metrics=metrics, test_mode=test_mode, logging=logging, save_folder=save_folder)
    res["stop"] = 1
    
    IOtool.write_json(res, osp.join(ROOT,"output", tid, stid+"_result.json"))
    
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_model_eva_api(tid, stid, dataname, model_path='', modelname='', metrics = [], senAttrList = [], tarAttrList = [], staAttrList= [], test_mode = True):
    """模型公平性提升
    :params tid:主任务ID
    :params stid:子任务id
    :params dataname:数据集名称
    :params modelname:模型名称
    :params algorithmname:优化算法名称
    """
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    logging = IOtool.get_logger(stid)
    if dataname in ["Compas", "Adult", "German"]:
        res = run_model_evaluate(dataname, model_path, modelname, metrics, senAttrList, tarAttrList, staAttrList, logging=logging)
    else:
        res = run_image_model_evaluate(dataname, model_path, modelname, metrics, test_mode, logging=logging)
    if "Consistency" in res.keys():
        res["Consistency"] = float(res["Consistency"])
    res["stop"] = 1
    
    IOtool.write_json(res, osp.join(ROOT,"output", tid, stid+"_result.json"))
    
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_data_debias_api(tid, stid, dataname, datamethod, senAttrList, tarAttrList, staAttrList):
    """数据集公平性提升
    :params tid:主任务ID
    :params stid:子任务id
    :params dataname:数据集名称
    :params datamethod:优化算法名称
    """
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    logging = IOtool.get_logger(stid)
    res = run_dataset_debias(dataname, datamethod, senAttrList, tarAttrList, staAttrList, logging=logging)
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, stid+"_result.json"))
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_verify(tid, AAtid, param):
    """鲁棒性形式化验证
    :params tid:主任务ID
    :params AAtid:子任务id
    :params param:参数
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    logging = IOtool.get_logger(AAtid)
    N = param['size']
    device = 'cpu'
    verify = vision_verify
    if param['dataset'] == 'mnist':
        mn_model = get_mnist_cnn_model()
        test_data, n_class = get_mnist_data(number=N, batch_size=10)
    if param['dataset'] == 'cifar10':
        mn_model = get_cifar_resnet18() if param['model']!= 'densenet' else get_cifar_densenet_model()
        test_data, n_class = get_cifar_data(number=N, batch_size=10)
    if param['dataset'] == 'gtsrb':
        mn_model = get_gtsrb_resnet18()
        test_data, n_class = get_gtsrb_data(number=N, batch_size=10)
    if param['dataset'] == 'mtfl':
        mn_model = get_MTFL_resnet18()
        test_data, n_class = get_MTFL_data(number=N, batch_size=10)
    if param['dataset'] == 'sst2':
        mn_model = get_lstm_demo_model() if param['model'] != 'transformer' else get_transformer_model()
        test_data, _ = get_sst_data(ver_num=N)
        n_class = 2
        verify = language_verify

    global LiRPA_LOGS
    input_param = {'interface': 'Verification',
                    'node': "中间结果可视化",
                    'input_param': {'model': mn_model,
                                    'dataset': test_data,
                                    'n_class': n_class,
                                    'up_eps': param['up_eps'],
                                    'down_eps': param['down_eps'],
                                    'steps': param['steps'],
                                    'device': device,
                                    "log_func":logging,
                                    'output_path': osp.join('output',tid,AAtid,"formal_img"),
                                    'task_id': f"{param['task_id']}"}}
    global result
    result = verify(input_param)
    result["stop"] = 1
    IOtool.write_json(result,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)


def run_concolic(tid, AAtid, dataname, modelname, norm, times):
    """测试样本自动生成
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataname:数据集名称
    :params modelname:模型名称
    :params norm:范数约束
    """
    
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    logging = IOtool.get_logger(AAtid)
    res = concolic.run_concolic(dataname.lower(), modelname.lower(), norm.lower(), int(times), osp.join(ROOT,"output", tid, AAtid), logging)  
    res["stop"]=1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_dataclean(tid, AAtid, dataname, upload_flag, upload_path):
    """异常数据检测
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataname:数据集名称
    :params upload_flag:上传标志
    :params upload_path:上传文件路径
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    logging = IOtool.get_logger(AAtid)
    res = dataclean.run_dataclean(dataname, int(upload_flag), upload_path, osp.join(ROOT,"output", tid, AAtid), logging)
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_envtest(tid,AAtid,matchmethod,frameworkname,frameversion):
    """系统环境分析
    :params tid:主任务ID
    :params AAtid:子任务id
    :params matchmethod:环境分析匹配机制
    :params frameworkname:适配框架名称
    :params frameversion:框架版本
    :output res:需保存到子任务json中的返回结果/路径
    """
    
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    logging = IOtool.get_logger(AAtid)
    res = env_test.run_env_frame(matchmethod,frameworkname,frameversion, osp.join(ROOT,"output", tid, AAtid), logging)
    # res = concolic.run_concolic(dataname, modelname, norm)  
    res["detection_result"]=IOtool.load_json(res["env_test"]["detection_result"])
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)
    
def run_coverage_neural(tid,AAtid,dataset,model, k, N):
    """单神经元测试准则
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params model: 模型名称
    :params k: 激活阈值
    :params N: 测试的图片数量
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    logging = IOtool.get_logger(AAtid)
    
    res = coverage.run_coverage_neural_func(dataset.lower(), model.lower(), float(k), int(N), osp.join(ROOT,"output", tid, AAtid), logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)
    
def run_coverage_layer(tid,AAtid,dataset,model, k, N):
    """神经层测试准则
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params model: 模型名称
    :params k: 激活阈值
    :params N: 测试的图片数量
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    logging = IOtool.get_logger(AAtid)
    res = coverage.run_coverage_layer_func(dataset.lower(), model.lower(), float(k), int(N), osp.join(ROOT,"output", tid, AAtid), logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_coverage_importance(tid, AAtid, dataset, model, n_imp, clus):
    """重要神经元覆盖测试准则
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params model: 模型名称
    :params n_imp: 重要神经元数目
    :params clus: 聚类数
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    logging = IOtool.get_logger(AAtid)
    res = coverage.run_coverage_importance_func(dataset.lower(), model.lower(), int(n_imp), int(clus), osp.join(ROOT,"output", tid, AAtid), logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)
  
def run_deepsst(tid,AAtid,dataset,modelname,pertube,m_dir):
    """敏感神经元测试准则
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params modelname: 模型名称
    :params pertube: 敏感神经元扰动比例
    :params m_dir: 敏感度值文件位置
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    logging = IOtool.get_logger(AAtid)
    res = deepsst.run_deepsst(dataset.lower(), modelname, float(pertube), m_dir, osp.join(ROOT,"output", tid, AAtid), logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)


def run_deeplogic(tid,AAtid,dataset,modelname):
    """逻辑神经元测试准则
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params modelname: 模型名称
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    logging = IOtool.get_logger(AAtid)
    from function import DeepLogic
    res = DeepLogic.run_deeplogic(dataset.lower(), modelname.lower(), osp.join(ROOT,"output", tid, AAtid), logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_frameworktest(tid,AAtid,modelname,framework):
    """开发框架安全结构度量
    :params tid:主任务ID
    :params AAtid:子任务id
    :params framework: 开发框架名称
    :params modelname: 模型名称
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    logging = IOtool.get_logger(AAtid)
    res = framework_test.run_framework_test_exec(modelname.lower(), framework, osp.join(ROOT,"output", tid, AAtid), logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_modelmeasure(tid,AAtid,dataset, modelname, naturemethod, natureargs, advmethod, advargs, measuremethod):
    """模型安全度量
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params modelname: 模型名称
    :params naturemethod: 自然样本生成方法
    :params natureargs: 自然样本扰动强度
    :params advmethod: 对抗样本生成方法
    :params advargs: 对抗样本扰动强度
    :params measuremethod: 安全度量维度
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    time.sleep(10)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    logging = IOtool.get_logger(AAtid)
    res = modelmeasure.run_modelmeasure(dataset.upper(), modelname.lower(), naturemethod, float(natureargs), advmethod.lower(), float(advargs), measuremethod, osp.join(ROOT,"output", tid, AAtid), logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)


def run_modulardevelop(tid,AAtid, dataset, modelname, tuner, init, epoch, iternum):
    """模型模块化开发
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params modelname: 模型名称
    :params tuner: 搜索方法
    :params* init: 初始化方法（仅DeepAlchemy方法需要）
    :params epoch: 搜索轮数
    :params iternum: 每次搜索迭代轮数
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    devive = IOtool.get_device()
    logging = IOtool.get_logger(AAtid)
    res = modulardevelop.run_modulardevelop(dataset.lower(), modelname.lower(), tuner.lower(), init.lower(), epoch, iternum, devive, osp.join(ROOT,"output", tid, AAtid), logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_dynamic_inference(image_dir, model_path):
    """模型模块化开发-在线推理
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :output res:需保存到子任务json中的返回结果/路径
    """
    res = modulardevelop.run_inference(image_dir, model_path)
    
    # checkpoint = torch.load(model_path, map_location=torch.device(0))
    # model.load_state_dict(checkpoint)
    # model = model.to(torch.device("cuda"))
    # 如何加载执行
    # imageLable = xxx()
    # return imageLable
    return res
    
from train_network import train_resnet_mnist, train_resnet_cifar10, eval_test, test_batch, robust_train

def run_adv_attack(tid, stid, dataname, model, methods, inputParam, sample_num=128):
    """对抗攻击评估
    :params tid:主任务ID
    :params stid:子任务id
    :params dataname:数据集名称
    :params model:模型名称
    :params methods:list，对抗攻击方法
    :params inputParam:输入参数
    """
    
    # 开始执行标记任务状态
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    logging = IOtool.get_logger(stid)
    inputParam['device'] = IOtool.get_device()
    device = torch.device(inputParam['device'])
    modelpath = osp.join("./model/ckpt", dataname.upper() + "_" + model.lower()+".pth")
    if (not osp.exists(modelpath)):
            logging.info("[模型获取]:服务器上模型不存在")
            if dataname.upper() == "CIFAR10":
                logging.info("[模型训练]:开始训练模型")
                train_resnet_cifar10(model, modelpath, logging, device)
                logging.info("[模型训练]:模型训练结束")
            elif dataname.upper() == "MNIST":
                logging.info("[模型训练]:开始训练模型")
                train_resnet_mnist(model, modelpath, logging, device)
                logging.info("[模型训练]:模型训练结束")
            else:
                logging.info(f"[模型训练]:不支持该数据集{dataname.upper()}")
                result={}
                result["stop"] = 1
                IOtool.write_json(result,osp.join(ROOT,"output", tid, stid+"_result.json"))
                IOtool.change_subtask_state(tid, stid, 3)
                IOtool.change_task_success_v2(tid)
                return 0
    if not osp.exists(osp.join(ROOT,"output", tid, stid)):
        os.mkdir(osp.join(ROOT,"output", tid, stid))
    resultlist={}
    all_num = 0
    for method in methods:
        logging.info("[执行对抗攻击]:正在执行{:s}对抗攻击".format(method))
        attackparam = inputParam[method]
        attackparam["save_path"] = osp.join(ROOT,"output", tid, stid)
        if "norm" in attackparam.keys() and attackparam["norm"]=="np.inf":
            attackparam["norm"]=np.inf
        resultlist[method] ,resultlist[method]["pic"], resultlist[method]["path"], resultlist[method]["num"] = run_adversarial(model, modelpath, dataname, method, attackparam, device, sample_num)
        logging.info("[执行对抗攻击中]:{:s}对抗攻击结束，攻击成功率为{}%".format(method,resultlist[method]["asr"]))
    # 统计缓存攻击用例
    # save_root = "dataset/adv_data"
    # num_all = 0
    # for dirpath,dirnames,filenames in os.walk(save_root):
    #     for filepath in filenames:
    #         if "adv_attack_" in filepath:
    #             datacatch = torch.load(osp.join(dirpath,filepath))
    #             num_all += len(datacatch['x'])
    #             del datacatch
    # logging.info('**************************')
    # logging.info(f'平台攻击用例总数：{num_all}')
    # logging.info('**************************')
    # logging.info("[执行对抗攻击]:对抗攻击执行完成，数据保存中")
    # resultlist["num_all"] = num_all
    resultlist["stop"] = 1
    IOtool.write_json(resultlist,osp.join(ROOT,"output", tid, stid+"_result.json"))
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)



def run_backdoor_attack(tid, stid, dataname, model, methods, inputParam):
    """后门攻击评估
    :params tid:主任务ID
    :params stid:子任务id
    :params dataname:数据集名称
    :params model:模型名称
    :params methods:list，后门攻击方法
    :params inputParam:输入参数
    """
    # 开始执行标记任务状态
    
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    logging = IOtool.get_logger(stid)
    inputParam['device'] = IOtool.get_device()
    if 'PoisoningAttackAdversarialEmbedding' in methods:
        feature=True
        modelpath = osp.join("./model/ckpt",dataname.upper() + "_" + model.lower()+"_1.pth")
    else:
        feature=False
        modelpath = osp.join("./model/ckpt",dataname.upper() + "_" + model.lower()+".pth")
    if (not osp.exists(modelpath)):
        logging.info("[模型获取]:服务器上模型不存在")
        if dataname.upper() == "CIFAR10":
            logging.info("[模型训练]:开始训练模型")
            train_resnet_cifar10(model, modelpath, logging, inputParam['device'], feature)
            logging.info("[模型训练]:模型训练结束")
        elif dataname.upper() == "MNIST":
            logging.info("[模型训练]:开始训练模型")
            train_resnet_mnist(model, modelpath, logging, inputParam['device'], feature)
            logging.info("[模型训练]:模型训练结束")
        else:
            logging.info(f"[模型训练]:不支持该数据集{dataname.upper()}")
            result={}
            result["stop"] = 1
            IOtool.write_json(result,osp.join(ROOT,"output", tid, stid+"_result.json"))
            IOtool.change_subtask_state(tid, stid, 3)
            IOtool.change_task_success_v2(tid)
            return 0
    res = {}
    logging.info("[执行后门攻击]:开始后门攻击")
    for method in methods:
        logging.info("[执行后门攻击]:正在执行{:s}后门攻击".format(method))
        res[method]={}
        attackparam = inputParam[method]
        save_path = osp.join(ROOT,"output", tid, stid)
        if not osp.exists(save_path):
            os.makedirs(save_path)
        inputParam[method]["save_path"] = save_path
        res[method]= run_backdoor(model, modelpath, dataname, method, pp_poison=inputParam[method]["pp_poison"], 
                                  save_num=inputParam[method]["save_num"], 
                                  target=inputParam[method]["target"],trigger=inputParam[method]["trigger"], device=inputParam["device"], 
                                  test_sample_num=inputParam[method]["test_sample_num"], train_sample_num=inputParam[method]["train_sample_num"], 
                                  nb_classes=10, method_param=inputParam[method], feature=feature)
        logging.info("[执行后门攻击]:{:s}后门攻击运行结束，投毒率为{}时，攻击成功率为{}%".format(method, inputParam[method]["pp_poison"], res[method]["attack_success_rate"]*100))
    res["stop"] = 1
    IOtool.write_json(res, osp.join(ROOT,"output", tid, stid+"_result.json"))
    
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
"""
因为3.2.4版本的torchattack会在每个对抗攻击函数的最后将图片归一化到（0,1）之间，
这意味着torchattack默认的输入图片是不经过Normalization的，
但该版本也没有设置过内部的normalization过程，因此需要在模型的开头加入一个自定义的Normal layer（继承Module类）
所以在构造对抗样本时输入的图片是没有经过Normalization的，否则图片会失真
"""
def run_dim_reduct(tid, stid, datasetparam, modelparam, vis_methods, adv_methods):
    """降维可视化
    :params tid:主任务ID
    :params stid:子任务id
    :params datasetparam:数据集参数
    :params modelparam:模型参数
    :params vis_methods:list，降维方法
    :params adv_methods:list，对抗攻击方法
    :params device:GPU
    """
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    logging = IOtool.get_logger(stid)
    device = IOtool.get_device()
    params = {
        "dataset": datasetparam,
        "model": modelparam,
        "out_path": osp.join(ROOT,"output", tid),
        "device": torch.device(device),
        "adv_methods":{"methods":adv_methods},
        "root":ROOT
    }
    root = ROOT
    dataset = datasetparam["name"]
    model_name = modelparam["name"]

    batchsize = get_batchsize(model_name,dataset)
    nor_data = torch.load(osp.join(root, f"dataset/data/{dataset}_NOR.pt"))
    nor_loader = get_loader(nor_data, batchsize=batchsize)
    logging.info( "[数据集获取]：获取{:s}数据集正常样本已完成.".format(dataset))

    model = modelparam["ckpt"]
    logging.info( "[加载被解释模型]：准备加载被解释模型{:s}".format(model_name))
    net = load_model_ex(model_name, dataset, device, root, reference_model=model, logging=logging)
    net = net.eval().to(device)
    logging.info( "[加载被解释模型]：被解释模型{:s}已加载完成".format(model_name))

    adv_loader = {}
    for adv_method in adv_methods:
        adv_loader[adv_method] = get_adv_loader(net, nor_loader, adv_method, params, batchsize=batchsize, logging=logging)
    logging.info( "[数据集获取]：获取{:s}对抗样本已完成".format(dataset))

    save_path = osp.join(ROOT,"output", tid, stid)
    if not osp.exists(save_path):
        os.mkdir(save_path)
    res = {}
    for adv_method in adv_methods:
        temp = dim_reduciton_visualize(vis_methods, nor_loader, adv_loader[adv_method], net, model_name, dataset, device, save_path)
        res[adv_method] = temp
        logging.info( "[数据分布降维解释]：{:s}对抗样本数据分布降维解释已完成".format(adv_method))
    res["stop"] = 1
    IOtool.write_json(res, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    print("interfase modify sub task state:",tid, stid)
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
    
def run_attrbution_analysis(tid, stid, datasetparam, modelparam, ex_methods, adv_methods, use_layer_explain):
    """对抗攻击归因解释
    :params tid:主任务ID
    :params stid:子任务id
    :params datasetparam:数据集参数
    :params modelparam:模型参数
    :params ex_methods:list，攻击解释方法
    :params adv_methods:list，对抗攻击方法
    :params device:GPU
    :params use_layer_explain: bool, 是否使用层间解释分析方法
    """
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    device = IOtool.get_device()
    logging = IOtool.get_logger(stid)
    params = {
        "dataset": datasetparam,
        "model": modelparam,
        "out_path": osp.join(ROOT,"output", tid, stid),
        "device": torch.device(device),
        "ex_methods":{"methods":ex_methods},
        "adv_methods":{"methods":adv_methods},
        "root":ROOT,
        "stid":stid
    }

    root = ROOT
    result = {}
    img_num = 20
    dataset = datasetparam["name"]
    model_name = modelparam["name"]

    batchsize = get_batchsize(model_name, dataset)
    nor_data = torch.load(osp.join(root, f"dataset/data/{dataset}_NOR.pt"))
    nor_loader = get_loader(nor_data, batchsize=batchsize)
    logging.info("[数据集获取]：获取{:s}数据集正常样本已完成.".format(dataset))

    # ckpt参数 直接存储模型object，不存储模型路径；可以直接带入load_model_ex函数中，该函数会自动根据输入作相应处理
    model = modelparam["ckpt"]
    logging.info( "[加载被解释模型]：准备加载被解释模型{:s}".format(model_name))
    net = load_model_ex(model_name, dataset, device, root, reference_model=model, logging=logging)
    net = net.eval().to(device)
    logging.info( "[加载被解释模型]：被解释模型{:s}已加载完成".format(model_name))

    adv_loader = {}
    for adv_method in adv_methods:
        adv_loader[adv_method] = get_adv_loader(net, nor_loader, adv_method, params, batchsize=batchsize, logging=logging)
    logging.info( "[数据集获取]：获取{:s}对抗样本已完成".format(dataset))

    save_path = osp.join(ROOT,"output", tid, stid)
    if not osp.exists(save_path):
        os.mkdir(save_path)
    
    logging.info( "[注意力分布图计算]：选择了{:s}解释算法".format(", ".join(ex_methods)))
    ex_images = attribution_maps(net, nor_loader, adv_loader, ex_methods, params, img_num, logging)
    result.update({"adv_ex":ex_images})

    if use_layer_explain == True:
        logging.info( "[已选择执行模型层间解释]：正在执行...")
        layer_ex = layer_explain(net, model_name, nor_loader, adv_loader, dataset, params["out_path"], device, img_num, logging)
        result.update({"layer_ex": layer_ex})
        logging.info( "[已选择执行模型层间解释]：层间解释执行完成")
    else:
        logging.info( "[未选择执行模型层间解释]：将不执行模型层间解释分析方法")
    result["stop"] = 1
    IOtool.write_json(result, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    print("interfase modify sub task state:",tid, stid)
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)

def run_adversarial_analysis(tid, stid, datasetparam, modelparam, ex_methods, vis_methods, adv_methods, use_layer_explain):
    """对抗攻击特征归因和降维解释集成接口
    :params tid:主任务ID
    :params stid:子任务id
    :params datasetparam:数据集参数
    :params modelparam:模型参数
    :params ex_methods:list, 特征归因解释方法
    :params vis_methods: list, 特征降维解释方法
    :params adv_methods:list, 对抗攻击方法
    :params device:GPU
    :params use_layer_explain: bool, 是否使用层间解释分析方法
    """
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    device = IOtool.get_device()
    logging = IOtool.get_logger(stid)
    params = {
        "dataset": datasetparam,
        "model": modelparam,
        "out_path": osp.join(ROOT,"output", tid, stid),
        "device": torch.device(device),
        "ex_methods":{"methods":ex_methods},
        "vis_methods":{"methods":vis_methods},
        "adv_methods":{"methods":adv_methods},
        "root":ROOT,
        "stid":stid
    }
    print(params)
    root = ROOT
    result = {}
    img_num = 20
    dataset = datasetparam["name"]
    model_name = modelparam["name"]

    batchsize = get_batchsize(model_name, dataset)
    batchsize = 8
    print(batchsize)
    nor_data = torch.load(osp.join(root, f"dataset/data/{dataset}_NOR.pt"))
    nor_loader = get_loader(nor_data, batchsize=batchsize)
    logging.info("[数据集获取]：获取{:s}数据集正常样本已完成.".format(dataset))

    # ckpt参数 直接存储模型object，不存储模型路径；可以直接带入load_model函数中，该函数会自动根据输入作相应处理
    model = modelparam["ckpt"]
    logging.info( "[加载被解释模型]：准备加载被解释模型{:s}".format(model_name))
    net = load_model_ex(model_name, dataset, device, root, reference_model=model, logging=logging)
    net = net.eval().to(device)
    logging.info( "[加载被解释模型]：被解释模型{:s}已加载完成".format(model_name))

    adv_loader = {}
    for adv_method in adv_methods:
        adv_loader[adv_method] = get_adv_loader(net, nor_loader, adv_method, params, batchsize=batchsize, logging=logging)
    logging.info( "[数据集获取]：获取{:s}对抗样本已完成".format(dataset))

    save_path = osp.join(ROOT,"output", tid, stid)
    if not osp.exists(save_path):
        os.mkdir(save_path)
    
    # 如果选择了归因方法
    if len(ex_methods) != 0:
        logging.info("已选择了特征归因解释算法，即将执行...")
        logging.info( "[注意力分布图计算]：选择了{:s}解释算法".format(", ".join(ex_methods)))
        ex_images = attribution_maps(net, nor_loader, adv_loader, ex_methods, params, img_num, logging)
        result.update({"adv_ex":ex_images})

        if use_layer_explain == True:
            logging.info( "[已选择执行模型层间解释]：正在执行...")
            layer_ex = layer_explain(net, model_name, nor_loader, adv_loader, dataset, params["out_path"], device, img_num, logging)
            result.update({"layer_ex": layer_ex})
            logging.info( "[已选择执行模型层间解释]：层间解释执行完成")
        else:
            logging.info( "[未选择执行模型层间解释]：将不执行模型层间解释分析方法")
    else:
        logging.info("当前未选择特征归因解释算法，跳过执行...")
    torch.cuda.empty_cache()
    # 如果选择了降维方法
    if len(vis_methods) != 0:
        logging.info("已选择了特征降维解释算法，即将执行...")
        result.update({"dim_ex":{}})
        for adv_method in adv_methods:
            temp = dim_reduciton_visualize(vis_methods, nor_loader, adv_loader[adv_method], net, model_name, dataset, device, save_path)
            result["dim_ex"][adv_method] = temp
            logging.info( "[数据分布降维解释]：{:s}对抗样本数据分布降维解释已完成".format(adv_method))
    else:
        logging.info("当前未选择特征降维解释算法，跳过执行...")

    logging.info("[执行完成] 当前攻击机理分析功能已全部完成！")
    result["stop"] = 1
    IOtool.write_json(result, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    print("interfase modify sub task state:",tid, stid)
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)

def run_lime(tid, stid, datasetparam, modelparam, adv_methods, mode):
    """多模态解释
    :params tid:主任务ID
    :params stid:子任务id
    :params datasetparam:数据集参数
    :params modelparam:模型参数
    :params adv_methods:list, 对抗攻击方法
    :params mode:数据模型信息:str, "text" or "image"
    """
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    device = IOtool.get_device()
    logging = IOtool.get_logger(stid)
    params = {
        "dataset": datasetparam,
        "model": modelparam,
        "out_path": osp.join(ROOT,"output", tid, stid),
        "device": torch.device(device),
        "adv_methods":{"methods":adv_methods},
        "mode":mode,
        "root":ROOT,
        "stid":stid
    }

    root = ROOT
    dataset = datasetparam["name"]
    model_name = modelparam["name"]
    model = modelparam["ckpt"]
    res = {}

    if mode == "image":
        logging.info("[数据集获取]：目前数据模态为图片类型")
    
        save_dir = os.path.join('./dataset/data/ckpt/upload.jpg')
        if os.path.exists(save_dir):
            image = Image.open(save_dir) 

            if dataset == "mnist":
                img = image.convert("L")
            img = image.convert('RGB')
        logging.info("[数据集获取]：获取{:s}数据样本已完成.".format(dataset))

        logging.info("[加载被解释模型]：准备加载被解释模型{:s}".format(model_name))
        net = load_torch_model(model_name)
        net = net.eval().to(device)

        img_x = load_image(device, img, dataset)
        label, _ = predict(net, img_x)
        logging.info("[加载被解释模型]：被解释模型{:s}已加载完成".format(model_name))

        # 将图片tensor去标准化，之后再输入torchattack中
        mean, std = get_normalize_para(dataset)
        re_trans = torchvision.transforms.Normalize(
                mean=tuple(-m / s for m, s in zip(mean, std)),
                std=tuple(1.0 / s for s in std),
            )
        img_x = re_trans(img_x)

        class_list = get_class_list(dataset, root)
        class_name = class_list[label.item()]

        save_path = params["out_path"]
        logging.info("[LIME图像解释]：正在对正常图片数据进行解释")
        res["adv_methods"] = adv_methods
        nor_img_lime, img_url, img_lime_url = lime_image_ex(img, net, model_name, dataset, device, save_path)
        res["nor"] = {"image":img_url,"ex_image":img_lime_url,"class_name":class_name,"kendalltau":"不适用"}
        logging.info("[LIME图像解释]：正常图片数据解释已完成")
        for adv_method in adv_methods:
            logging.info("[数据集获取]：正在生成图像{:s}对抗样本".format(adv_method))
            adv_img, adv_label = sample_untargeted_attack(dataset, adv_method, net, img_x, label, device, root)
            logging.info("[数据集获取]：图像{:s}对抗样本已生成".format(adv_method))
            class_name = class_list[adv_label.item()]
            save_path = params["out_path"]
            logging.info("[LIME图像解释]：正在对{:s}图片数据进行解释".format(adv_method))
            adv_img_lime, img_url, img_lime_url = lime_image_ex(adv_img, net, model_name, dataset, device, save_path, imagetype=adv_method)
            kendall_value, _ = kendalltau(np.array(nor_img_lime,dtype="float64"),np.array(adv_img_lime,dtype="float64"))
            kendall_value = round(kendall_value, 4)
            res[adv_method] = {"image":img_url, "ex_image":img_lime_url,"class_name":class_name,"kendalltau":kendall_value}
            logging.info("[LIME图像解释]：{:s}图片数据解释已完成".format(adv_method))
        logging.info("[LIME图像解释]：LIME解释已全部完成")
    else:
        # 数据为文本模态
        logging.info("[数据集获取]：目前数据模态为文本类型")
        text = datasetparam['data']
        res["adv_methods"] = adv_methods
        logging.info("[数据集获取]：获取{:s}数据样本已完成.".format(dataset))

        logging.info("[加载模型中]：正在加载{:s}模型.".format(model_name))
        model = load_text_model(model_name)
        tokenizer = model.tokenizer
        model_wrapper = textattack.models.wrappers.PyTorchModelWrapper(model, tokenizer)
        class_names = ["negitive", "positive"]
        logging.info("[加载模型中]：{:s}模型已加载完成.".format(model_name))

        logging.info("[LIME文本解释]：正在对正常文本数据进行解释.")
        ex_nor = lime_text_ex(model_wrapper, text, class_names=class_names)
        logging.info("[LIME文本解释]：正常文本数据解释分析完成.")
        res['nor'] = {"class_names": ex_nor[0], 
            "predictions":ex_nor[1], 
            "regression_result":ex_nor[2], 
            "explain_res":ex_nor[3], 
            "raw_js":ex_nor[4]
            }
        logging.info("[LIME文本解释]：正在对对抗文本数据进行解释.")
        for adv_method in adv_methods:
            logging.info(f"[LIME文本对抗攻击]：采用{adv_method}对抗攻击方法生成对抗样本中...")
            adv_text = text_attack(model_wrapper, adv_method, text)
            ex_adv = lime_text_ex(model_wrapper, adv_text, class_names=class_names)
            logging.info(f"[LIME文本解释]：{adv_method}对抗文本攻击数据解释分析完成.")
            res[adv_method] = {"class_names": ex_adv[0], 
                "predictions":ex_adv[1], 
                "regression_result":ex_adv[2], 
                "explain_res":ex_adv[3], 
                "raw_js":ex_adv[4]
                }
        logging.info("[LIME文本解释]：LIME解释已全部完成")
    res["stop"] = 1  
    IOtool.write_json(res, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    print("interfase modify sub task state:", tid, stid)
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
    
def verify_img(tid, stid, net, dataset, eps, pic_path):
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    logging = IOtool.get_logger(stid)
    b1=[]
    b2=[]
    print(net, dataset)

    lb1,ub1,lb2,ub2,predicted,score_IBP,score_CROWN=auto_verify_img(net, dataset, eps, pic_path)
    categories=[]
    for i in range(len(lb1)):
        b1.append([round(lb1[i],4),round(ub1[i],4)])
        b2.append([round(lb2[i],4),round(ub2[i],4)])
        categories.append(f'f_{i}')
    resp={'boundary1':b1,'boundary2':b2,'categories':categories,'predicted':predicted,
          'score_IBP':score_IBP,'score_CROWN':score_CROWN}
    
    IOtool.write_json(resp, osp.join(ROOT,"output", tid, stid+"_result.json"))
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
    return resp


def submitAandB(tid, stid, a, b):
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
    return a + b

def reach(tid, stid, dataset, pic_path,label, target_label):
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    logging = IOtool.get_logger(stid)
    save_path = osp.join("output", tid, stid)
    logging.info(f"The reachability task starts ，dateset: {dataset}")
    base=os.path.join(os.getcwd(),"model","ckpt")
    base_path=os.path.join(base,'reach_checkpoints')
    model = reachNet()
    if dataset=='CIFAR10':  
        logging.info(f"Start to load CNN-3layer")
        model.load_state_dict(torch.load(os.path.join(base_path,'cifar_torch_net.pth'), map_location=torch.device('cpu')))
    else:
        logging.info(f"Start to load CNN-3layer")
        model.load_state_dict(torch.load(os.path.join(base_path,'mnist_torch_net.pth'), map_location=torch.device('cpu')))
    logging.info(f"End of model loading")
    model.eval()
    transf = transforms.ToTensor()
    logging.info(f"Start to load the uploaded image")
    img = cv2.imread(pic_path)
    image=transf(img)
    image=torch.unsqueeze(image, 0)
    label=torch.tensor(int(label))
    target_label=torch.tensor(int(target_label))

    attack_block = (1,1)
    epsilon = 0.02
    relaxation = 0.01
    logging.info(f"reachability verification")
    reach_model = ReachMethod(model, image, label, save_path,
                         attack_block=attack_block,
                         epsilon=epsilon,
                         relaxation=relaxation)
    output_sets = reach_model.reach()
    # num 越小越快
    sims = reach_model.simulate(num=1000)

    # Plot output reachable sets and simulations
    dim0, dim1 = label.numpy(), target_label.numpy()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    logging.info(f"Output data process, reachable area drawing")
    
    for item in output_sets:
        out_vertices = item[0]
        plot_polytope2d(out_vertices[:, [dim0, dim1]], ax, color='b', alpha=1.0, edgecolor='k', linewidth=0.0,zorder=2)
    ax.plot(sims[:,dim0], sims[:,dim1],'k.',zorder=1)
    minnum = min(sims[:,dim0]) if min(sims[:,dim0]) > min(sims[:,dim1]) else min(sims[:,dim1])
    maxnum = max(sims[:,dim0]) if max(sims[:,dim0]) > max(sims[:,dim1]) else max(sims[:,dim1])
    x = np.linspace(minnum, maxnum, 1000)
    y = x
    ax.plot(x, y, 'r', linewidth = 2)
    ax.autoscale()
    plt.tight_layout()
    # plt.show()
    pt_dir=os.path.dirname(pic_path)
    outpath = osp.join(ROOT, "output", tid, stid, 'output.png')
    plt.savefig(outpath)
    plt.close()
    logging.info(f"The reachable areas is drawn. The reachability verification is complete")
    resp={"path":osp.join("/static", "output", tid, stid, 'output.png')}
    resp['input']=f'static/img/tmp_imgs/{tid}/{stid}.png'
    resp["stop"] = 1
    IOtool.write_json(resp, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
    return resp

def run_detect(tid, stid, defense_methods, adv_dataset, adv_model, adv_method, adv_nums, adv_file_path):
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    # device = IOtool.get_device()
    logging = IOtool.get_logger(stid)
    detect_rate_dict = {}
    if "CARTL" in defense_methods:
        # 调换顺序，将CARTL放在最后执行
        defense_methods.remove("CARTL")
        defense_methods.append("CARTL")
    for defense_method in defense_methods:
        logging.info("开始执行防御任务{:s}".format(defense_method))
        detect_rate, no_defense_accuracy = detect(adv_dataset, adv_model, adv_method, adv_nums, defense_method, adv_file_path,logging)
        detect_rate_dict[defense_method] = round(detect_rate, 4)
        logging.info("{:s}防御算法执行结束，对抗鲁棒性为：{:.3f}".format(defense_method,round(detect_rate, 4)))
    no_defense_accuracy_list = no_defense_accuracy.tolist() if isinstance(no_defense_accuracy, np.ndarray) else no_defense_accuracy
    response_data = {
        "detect_rates": detect_rate_dict,
        "no_defense_accuracy": no_defense_accuracy_list
    }
    response_data["stop"] = 1
    IOtool.write_json(response_data, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
    return response_data

def detect(adv_dataset, adv_model, adv_method, adv_nums, defense_methods, adv_examples=None, logging=None):
    from model.model_net.resnet import ResNet18 
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    # device = IOtool.get_device()
    if torch.cuda.is_available():
        print("got GPU")
    logging.info("加载模型{:s}".format(adv_model))
    if adv_dataset == 'CIFAR10':
        mean = [0.4914, 0.4822, 0.4465]
        std = [0.2023, 0.1994, 0.2010]
        if adv_model == 'ResNet18':
            model = ResNet18()
            checkpoint = torch.load(osp.join(ROOT,'model/model-cifar-resnet18/model-res-epoch85.pt'))
        elif adv_model == 'VGG16':
            model = vgg16()
            model.classifier[6] = nn.Linear(4096, 10)
            checkpoint = torch.load(osp.join(ROOT,'model/model-cifar-vgg16/model-vgg16-epoch85.pt'))
        else:
            raise Exception('CIFAR10 can only use ResNet18 and VGG16!')
        model.load_state_dict(checkpoint)
        model = model.to(device)
    elif adv_dataset == 'MNIST':
        mean = (0.1307,)
        std = (0.3081,)
        if adv_model == 'SmallCNN':
            model = SmallCNN()
            checkpoint = torch.load(osp.join(ROOT,'model/model-mnist-smallCNN/model-nn-epoch61.pt'))
        elif adv_model == 'VGG16':
            model = vgg16()
            model.features[0] = nn.Conv2d(1, 64, kernel_size=3, padding=1)
            model.classifier[6] = nn.Linear(4096, 10)
            checkpoint = torch.load(osp.join(ROOT,'model/model-mnist-vgg16/model-vgg16-epoch32.pt'))
        else:
            raise Exception('MNIST can only use SmallCNN and VGG16!')
        model.load_state_dict(checkpoint)
        model = model.to(device).eval()
    logging.info("{:s}模型加载结束".format(adv_model))
    print(defense_methods)
    if defense_methods not in ['Pixel Defend', 'Pixel Defend Enhanced'] and adv_method == 'BPDA':
        raise Exception('BPDA can only use to attack Pixel Defend and Pixel Defend Enhanced!')
    if defense_methods == 'JPEG':
        detector = Jpeg(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Feature Squeeze':
        detector = feature_squeeze(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Twis':
        detector = Twis(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Rgioned-based':
        detector = RegionBased(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Pixel Deflection':
        detector = Pixel_Deflection(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Label Smoothing':
        detector = Label_smoothing(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Spatial Smoothing':
        detector = Spatial_smoothing(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Gaussian Data Augmentation':
        detector = Gaussian_augmentation(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Total Variance Minimization':
        detector = Total_var_min(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Pixel Defend':
        detector = Pixel_defend(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Pixel Defend Enhanced':
        detector =  Pixel_defend_enhanced(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'InverseGAN':
        detector = Inverse_gan(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'DefenseGAN':
        detector = Defense_gan(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Madry':
        detector = Madry(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'FastAT':
        detector = FastAT(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'TRADES':
        detector = Trades(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'FreeAT':
        detector = FreeAT(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'MART':
        detector = Mart(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'CARTL':
        detector = Cartl(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Activation':
        detector = Activation_defence(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Spectral Signature':
        detector = Spectral_signature(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Provenance':
        detector = Provenance_defense(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Neural Cleanse L1':
        detector = Neural_cleanse_l1(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Neural Cleanse L2':
        detector = Neural_cleanse_l2(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'Neural Cleanse Linf':
        detector = Neural_cleanse_linf(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == 'SAGE':
        detector = Sage(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)
    elif defense_methods == "STRIP":
        detector = Strip(model, mean, std, adv_examples=adv_examples, adv_method=adv_method, adv_dataset=adv_dataset, adv_nums=adv_nums, device=device)

    _, _, detect_rate, no_defense_accuracy = detector.detect()
    
    
    return detect_rate, no_defense_accuracy


def run_side_api(trs_file, method, tid, stid):
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    device = IOtool.get_device()
    logging = IOtool.get_logger(stid)
    logging.info("开始执行侧信道分析")
    res={}
    if method in ['cpa','dpa']:
        logging.info("当前分析文件为{:s}，分析方法为{:s}，分析时间较久，约需2分钟".format(trs_file, method))
    else:
        logging.info("当前分析文件为{:s}，分析方法为{:s}".format(trs_file, method))
    number = trs_file.split(".trs")[0].split("_")[-1]
    # outpath = osp.join(ROOT,"output", tid,stid + "_" + method+"_"+number+"_out.txt")
    # trs_file_path = osp.join(ROOT,"dataset/Trs/samples",trs_file)
    if method in ['cpa', 'dpa', 'hpa']:
        trs_file_path = osp.join(ROOT, "dataset/Trs/samples", method, "elmotrace"+number, trs_file)
        outpath = osp.join(ROOT,"output", tid,stid + "_" + method+"_"+number+"_out.txt")
    elif method == "dpa":
        trs_file_path = osp.join(ROOT, "dataset/Trs/samples", "cpa", "elmotrace"+number, trs_file)
        outpath = osp.join(ROOT,"output", tid,stid + "_" + method+"_"+number+"_out.txt")
    elif method == "spa":
        trs_file_path = osp.join(ROOT, "dataset/Trs/samples", method, trs_file)
        outpath = osp.join(ROOT,"output", tid, stid)
        if not osp.exists(outpath):
            os.makedirs(outpath)
    elif method in ['ttest', "x2test"]:
        trs_file_path = osp.join(ROOT, "dataset/Trs/samples", "cpa", "elmotrace"+number, trs_file)
        outpath = osp.join(ROOT,"output", tid,stid + "_" + method+"_"+number+"_out.txt")
    use_time = run_side(trs_file_path, method, outpath)
    res[method] = {}
    
    index = 128+ int(number)
    # res[method].append([float(s) for s in line.split()])
    if method in ["cpa","dpa","hpa","ttest", "x2test"]:
        res[method]["Y"] = []
        res[method]["X"] = []
        count = 9 if method == 'hpa' else 100
        cur = 0
        for line in open(outpath, 'r'):
            values = [float(s) for s in line.split()]
            if method in ['x2test', 'ttest'] :
                count == 127 if len(values) >127 else len(values)
            Y = []
            i = 0
            while i < count:
                Y.append(values[i])
                i += 1
            if cur == index:
                res[method]["true"] = Y
            if cur == index+1:
                res[method]["false"] = Y
            else:
                res[method]["Y"].append(Y)
            cur += 1
        j = 1
        while j < (count+1):
            res[method]["X"].append(j)
            j += 1
    else:
        # 其他方法结果处理
        pass
    if method in ["cpa","dpa"]:
        logging.info("分析方法{:s}执行结束，运行100次耗时{:s}s".format(method,str(round(use_time,1))))
        logging.info("系统平均耗时{:s}s".format(method,str(round(use_time/100,1))))
        res[method]["runTime"] = use_time/100
    else:
        logging.info("分析方法{:s}执行结束，耗时{:s}s".format(method,str(round(use_time,1))))
        res[method]["runTime"] = use_time
    logging.info("侧信道分析执行结束！")
    res["stop"] = 1
    IOtool.write_json(res, osp.join(ROOT,"output", tid, stid+"_result.json"))
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)

def knowledge_consistency(tid, stid, arch,dataset,img_path,layer):
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    device = IOtool.get_device()
    logging = IOtool.get_logger(stid)
    base=os.path.join(os.getcwd(),"model","ckpt")
    base_path=os.path.join(base,'knowledge_consistency_checkpoints')
    if arch=='vgg16_bn' and dataset=='mnist':
        conv_layer=30
        model_path1=os.path.join(base_path,'checkpoint_mnist_vgg16_bn_lr-2_sd0.pth.tar')
        model_path2=os.path.join(base_path,'checkpoint_mnist_vgg16_bn_lr-2_sd5.pth.tar')
        resume=os.path.join(base_path,f'{dataset}_{arch}','checkpoint_L30__a0.1_lr-4.pth.tar')
    elif arch=='vgg16_bn' and dataset=='cifar10':
        conv_layer=30
        model_path1=os.path.join(base_path,'checkpoint_cifar10_vgg16_bn_lr-2_sd0.pth.tar')
        model_path2=os.path.join(base_path,'checkpoint_cifar10_vgg16_bn_lr-2_sd5.pth.tar')
        resume=os.path.join(base_path,f'{dataset}_{arch}','checkpoint_L30__a0.1_lr-4.pth.tar')
    elif arch=='resnet18' and dataset=='mnist':
        conv_layer=3
        model_path1=os.path.join(base_path,'checkpoint_mnist_resnet18_lr-2_sd0.pth.tar')
        model_path2=os.path.join(base_path,'checkpoint_mnist_resnet18_lr-2_sd5.pth.tar')
        resume=os.path.join(base_path,f'{dataset}_{arch}','checkpoint_L3__a0.1_lr-4.pth.tar')
    elif arch=='resnet18' and dataset=='cifar10':
        conv_layer=3
        model_path1=os.path.join(base_path,'checkpoint_cifar10_resnet18_lr-2_sd0.pth.tar')
        model_path2=os.path.join(base_path,'checkpoint_cifar10_resnet18_lr-2_sd5.pth.tar')
        resume=os.path.join(base_path,f'{dataset}_{arch}','checkpoint_L3__a0.1_lr-3.pth.tar')
    else:
        print(arch,dataset)
        return None
    if dataset=='mnist':
        transform=transforms.Compose([transforms.Resize((224,224)),transforms.Grayscale(num_output_channels=3),
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,))])
    elif dataset=='cifar10':
        transform=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),
                                  transforms.Normalize(mean=[0.4914, 0.4822, 0.4465], std=[0.2023, 0.1994, 0.2010])])
    net1 = zoomodels.__dict__[arch](num_classes=10)
    load_checkpoint(model_path1, net1)
    net2 = zoomodels.__dict__[arch](num_classes=10)
    load_checkpoint(model_path2, net2)
    img = Image.open(img_path)
    img = img.convert('RGB')

    x_ori = transform(img)
    y = net1(x_ori.unsqueeze(0))
    y = np.argmax(y.cpu().detach().numpy())
    x = get_feature(x_ori, net1,arch,conv_layer)
    input_size = x.shape
    output_size = x.shape
    model = zoomodels.LinearTester(input_size,output_size, affine=False, bn = False, instance_bn=True).cuda()
    checkpoint = torch.load(resume, map_location=torch.device(0))
    model.load_state_dict(checkpoint['state_dict'])
    del checkpoint
    input = get_feature(x_ori,net1,arch,conv_layer)
    target = get_feature(x_ori,net2,arch,conv_layer)
    model.eval()
    output, output_n, output_contrib, res = model.val_linearity(input.unsqueeze(0).cuda())
    t=0
    img_name=os.path.basename(img_path).split('.')[0]
    pic_dir=os.path.dirname(img_path)
    delta = target - output
    # for t in range(len(output)):
    t=layer
    plt.figure(frameon=False)
    plt.axis('off')
    plt.imshow(output[t], cmap='jet', norm=None, vmin=output.min(), vmax=output.max())
    plt.savefig(os.path.join(pic_dir,stid+f'_output_{t}.png'),bbox_inches='tight')
    plt.close()
    plt.figure(frameon=False)
    plt.axis('off')
    plt.imshow(input[t], cmap='jet', norm=None, vmin=input.min(), vmax=input.max())
    plt.savefig(os.path.join(pic_dir,stid+f'_input_{t}.png'),bbox_inches='tight')
    plt.close()
    plt.figure(frameon=False)
    plt.axis('off')
    plt.imshow(target[t], cmap='jet', norm=None, vmin=target.min(), vmax=target.max())
    plt.savefig(os.path.join(pic_dir,stid+f'_target_{t}.png'),bbox_inches='tight')
    plt.close()
    plt.figure(frameon=False)
    plt.axis('off')
    plt.imshow(delta[t], cmap='jet', norm=None, vmin=delta.min(), vmax=delta.max())
    plt.savefig(os.path.join(pic_dir,stid+f'_delta_{t}.png'),bbox_inches='tight')
    plt.close()
    l2 = torch.norm(delta, p=2).numpy().tolist()
    layers = len(target)
    resp={'l2':l2,'input':f'static/output/{tid}/{stid}/input.png',
                'output':f'static/output/{tid}/{stid}/{stid}_output_{layer}.png',
                'target':f'static/output/{tid}/{stid}/{stid}_target_{layer}.png',
                'delta':f'static/output/{tid}/{stid}/{stid}_delta_{layer}.png',
            }
    resp["stop"] = 1
    IOtool.write_json(resp, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
    return resp

from function.ensemble import ensemble_defense

from dataset import ArgpLoader
# from function.ex_methods.module.train_model import
from function.ensemble import paca_detect
def load_dataset(dataset, batchsize, rate=0.1):
    if dataset.lower() == "mnist":
        transform = transforms.Compose([transforms.Resize(28), transforms.ToTensor(), transforms.Normalize([0.1307], [0.3081])])
        train_dataset = mnist.MNIST('./dataset/data/MNIST', train=True, transform=transform, download=True)
        test_dataset = mnist.MNIST('./dataset/data/MNIST', train=False, transform=transform, download=False)
        channel = 1
    elif dataset.lower() == "cifar10":
        transform = transforms.Compose([transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip(),transforms.ToTensor(),transforms.Normalize(mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225])])
        # mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225]
        train_dataset = CIFAR10('./dataset/data/CIFAR10', train=True, transform=transform, download=True)
        test_dataset = CIFAR10('./dataset/data/CIFAR10', train=False, transform=transform, download=False)
        channel = 3
        
    test_sample_num = int(len(test_dataset) * rate)
    train_sample_num = int(len(train_dataset) * rate)
    test_sample_size = len(test_dataset) - test_sample_num
    train_sample_size = len(train_dataset) - train_sample_num
    
    _, train_dataset_sample = torch.utils.data.random_split(train_dataset, [train_sample_size, train_sample_num])
    _, test_dataset_sample = torch.utils.data.random_split(test_dataset, [test_sample_size, test_sample_num])
    test_loader = DataLoader(test_dataset_sample, batch_size=batchsize,shuffle=False)
    train_loader = DataLoader(train_dataset_sample, batch_size=batchsize, shuffle=True,num_workers=2)
    # train_loader = DataLoader(train_dataset, batch_size=batchsize, shuffle=True,num_workers=2)
    # test_loader = DataLoader(test_dataset, batch_size=batchsize,shuffle=False)
    return train_loader, test_loader, channel

def load_model_net(modelname, dataset, upload={'flag':0, 'upload_path':None}, channel=3, logging=None, device=None):
    from model.model_net.resnet_attack import ResNet18, ResNet34, ResNet50, ResNet101, ResNet152
    if upload['flag'] == 1:
        channel = upload['channel']
        if not osp.exsits(upload['upload_path']):
            error = "{} is not exist".format(upload_path)
            raise ValueError(error)
        modelpath = upload['upload_path']
    else: 
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        modelpath = osp.join("./model/ckpt", dataset.upper() + "_" + modelname.lower()+".pth")
        if (not osp.exists(modelpath)):
            logging.info("[模型获取]:服务器上模型不存在")
            if dataset.upper() == "CIFAR10":
                logging.info("[模型训练]:开始训练模型")
                train_resnet_cifar10(modelname, modelpath, logging, device)
                logging.info("[模型训练]:模型训练结束")
                channel = 3
            elif dataset.upper() == "MNIST":
                logging.info("[模型训练]:开始训练模型")
                train_resnet_mnist(modelname, modelpath, logging, device)
                logging.info("[模型训练]:模型训练结束")
                channel = 1
            else:
                logging.info(f"[模型训练]:不支持该数据集{dataset.upper()}")
                error = f"{dataset.upper()} is not support"
                raise ValueError(error)
    model = eval(modelname)(channel)
    logging.info("[模型获取]:加载模型")
    checkpoint = torch.load(modelpath)
    try:
        model.load_state_dict(checkpoint)
    except:
        model.load_state_dict(checkpoint['net'])
    return model
from function.ex_methods.module.func import get_loader
from function.attack import run_get_adv_data, run_get_adv_attack, Attack_Obj
def get_load_adv_data(datasetparam, modelparam, adv_methods, adv_param, model, test_loader, device, batchsize, logging=None):
    adv_save_root = "dataset/adv_data"
    adv_loader = {}
    if not osp.exists(adv_save_root):
        os.makedirs(adv_save_root)
    
    for i, adv_method in enumerate(adv_methods): 
        logging.info("[模型测试阶段] 正在运行对抗样本攻击:{:s}...[{:d}/{:d}]".format(adv_method, i + 1, len(adv_methods)))
        if 'eps' in adv_param[adv_method]:
            eps = adv_param[adv_method]['eps']
        else:
            eps = 1
        if 'step' in adv_param[adv_method]:
            steps = adv_param[adv_method]['step']
        else:
            steps = 1
        path = osp.join(adv_save_root, "adv_{:s}_{:s}_{:s}_{:04d}_{:.5f}.pt".format(
                            adv_method, modelparam['name'], datasetparam['name'], steps, eps))
        if osp.exists(path):
            logging.info("[加载数据集]：检测到缓存{:s}对抗样本，直接加载缓存文件".format(adv_method))
            data = torch.load(path)
        else:
            logging.info("[加载数据集]：未检测到缓存的{:s}对抗样本，将重新执行攻击算法并缓存".format(adv_method))
            attack_info = run_get_adv_data(dataset_name = datasetparam['name'], model = model, dataloader = test_loader, device = device, method= adv_method, attackparam=adv_param[adv_method])
            data = {
                'x':torch.tensor(attack_info[0]),
                'y':torch.tensor(attack_info[2])
            }
            torch.save(data, path)

        data_temp = {
            'x':[torch.tensor(data['x'])],
            'y':[torch.tensor(data['y'])]
        }
        adv_loader[adv_method] = get_loader(data_temp, batchsize)
    return adv_loader

def run_group_defense(tid,stid, datasetparam, modelparam, adv_methods, adv_param, defense_methods):
    """群智化防御，包含PACA、博弈、集成、群智、CAFD等
    :params tid:主任务ID
    :params stid:子任务id
    :params datasetparam:数据集参数
    :params modelparam:模型参数
    :params adv_methods:list，对抗攻击方法
    :params adv_param:dict,对抗攻击参数
    :params defense_methods:list，集成防御方法
    """
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    device = IOtool.get_device()
    logging = IOtool.get_logger(stid)
    batchsize = 128
    result={
        "AdvAttack":{
            "atk_acc":{},
            "atk_asr":{},
            },
        "AdvTrain":{
            "def_acc":{},
            "def_asr":{},
            "rbst_model_path":{}
        },
        "sys":{}
    }
    # 加载数据
    train_loader, test_loader, channel = load_dataset(datasetparam['name'], batchsize=batchsize, rate=0.1)
    # 加载模型
    model = load_model_net(modelparam['name'], datasetparam['name'], channel=channel, logging=logging)
    result["AdvAttack"]["test_acc"] = eval_test(model.eval().to(device), test_loader, device=device)
    logging.info("[模型训练阶段] 模型训练完成，测试准确率：{:.3f}% ".format(result["AdvAttack"]["test_acc"]))
    # 记载对抗样本
    adv_loader = get_load_adv_data(datasetparam, modelparam, adv_methods, adv_param, model, test_loader, device, batchsize, logging=logging)
    # 计算对抗攻击成功率
    for i, adv_method in enumerate(adv_methods):
        result["AdvAttack"]["atk_acc"][adv_method] = eval_test(model.eval().to(device), adv_loader[adv_method], device=device)
        result["AdvAttack"]["atk_asr"][adv_method] = 100 - result["AdvAttack"]["atk_acc"][adv_method]
        logging.info("[模型测试阶段] {:s}对抗样本测试准确率：{:.3f}% ".format(adv_method, result["AdvAttack"]["atk_acc"][adv_method]))
    copy_model1 = copy.deepcopy(model)
    if "PACA" in defense_methods:
        result.update({"PACA":{}})
        logging.info("[模型测试阶段] 即将运行【自动化攻击监测、算法加固】算法：paca_detect")
        params = {
            "out_path": osp.join(ROOT,"output", tid, stid),
            "device": torch.device(device),
        }
        result["PACA"]=paca_detect.run(model=copy_model1, test_loader=test_loader, adv_dataloader=adv_loader, params=params,
                        log_func=logging.info, channel=channel)
        logging.info("[模型测试阶段]【自动化攻击监测、算法加固】方法：paca_detect运行结束")
        logging.info('[软硬件协同安全攻防测试] 测试任务编号：{:s}'.format(tid))
        if len(defense_methods)==1:
            result['stop'] = 1
            IOtool.write_json(result, osp.join(ROOT,"output", tid, stid+"_result.json")) 
            IOtool.change_subtask_state(tid, stid, 2)
            IOtool.change_task_success_v2(tid)
            return
        else:
            defense_methods.remove("PACA")
    if "CAFD" in defense_methods:
        result.update({"CAFD":{
            "CAFD_acc":{},
            "CAFD_asr":{},
        }})
        logging.info("[模型测试阶段] 即将运行【基于类激活图的扰动过滤】算法：CAFD")
        from function.ensemble.CAFD.train_or_test_denoiser import cafd
        temp = {}
        for method in adv_methods:
            data_size = 28 if channel == 1 else 32
            itr = 10 if channel == 1 else 30
            temp = cafd(target_model=copy_model1, dataloader=test_loader, method=method, adv_param=adv_param[method], channel=channel, data_size=data_size, weight_adv=5e-3,
            weight_act=1e3, weight_weight=1e-3, lr=0.001, itr=itr,
            batch_size=batchsize, weight_decay=2e-4, print_freq=10, save_freq=2, device=device, dataset=datasetparam['name'])
            result["CAFD"]['CAFD_acc'][method] = temp['prec']*100
            result["CAFD"]['CAFD_asr'][method] = 100 - result["CAFD"]['CAFD_acc'][method]
        logging.info("[模型测试阶段] 【基于类激活图的扰动过滤】算法：CAFD运行结束")
        if len(defense_methods)==1:
            result['stop'] = 1
            IOtool.write_json(result, osp.join(ROOT,"output", tid, stid+"_result.json")) 
            IOtool.change_subtask_state(tid, stid, 2)
            IOtool.change_task_success_v2(tid)
            return
        else:
            defense_methods.remove("CAFD")
    # 对抗训练 & 攻防博弈
    logging.info('[攻防推演阶段]即将执行【自动化攻防测试】算法')
    logging.info('[攻防推演阶段]即将进行攻防推演，选择预设的{:d}种模型，调整参数并开始攻防推演'.format(len(adv_methods)))
    arch = modelparam['name']
    task = datasetparam['name']
    robust_models={}
    for i, method in enumerate(adv_methods):
        logging.info('[软硬件协同安全攻防测试] 测试任务编号：{:s}'.format(tid))
        logging.info('[攻防推演阶段]使用对抗样本算法{:s}生成的样本作为鲁棒训练数据，训练鲁棒性强的模型'.format(method))
        """专门针对上传的对抗样本设计，仅做测试不做鲁棒训练"""
        if "eps" not in adv_param[method].keys():
            adv_param[method]["eps"] = 1
        _eps = adv_param[method]["eps"]
        result["AdvAttack"][method] = {}
        for rate in [0.9, 1.0, 1.1]:
            adv_param[method]["eps"] = _eps * rate
            copy_model = copy.deepcopy(model)
            logging.info('[攻防推演阶段]使用对抗样本算法{:s}生成的样本作为鲁棒训练数据，eps参数为：{:.3f}'.format(method, float(
                adv_param[method]["eps"])))
            def_method = "{:s}_{:.5f}".format(method, adv_param[method]["eps"])
            cahce_weights = IOtool.load(arch=arch, task=task, tag=def_method)
            if cahce_weights is None:
                logging.info('[攻防推演阶段]缓存模型不存在，开始模型鲁棒训练（这步骤耗时较长）')
                logging.info('[软硬件协同安全攻防测试] 测试任务编号：{:s}'.format(tid))
                # attack = run_get_adv_attack(dataset_name = datasetparam['name'], model = model, dataloader = test_loader, device = device, method= method, attackparam=adv_param[method])
                attack = Attack_Obj(dataset_name = datasetparam['name'], model = model, dataloader = test_loader, device = device, method= method, attackparam=adv_param[method])
                rst_model = robust_train(copy_model, train_loader, test_loader,
                                                     adv_loader=adv_loader[method], attack=attack, device=device,  epochs=10, method=method, adv_param=adv_param[method],
                                                     atk_method=method, def_method=def_method
                                                     )
                IOtool.save(model=rst_model, arch=arch, task=task, tag=def_method)
            else:
                logging.info('[攻防推演阶段]从默认文件夹载入缓存模型')
                temp_model = copy.deepcopy(copy_model)
                temp_model.load_state_dict(cahce_weights)
                rst_model = copy.deepcopy(temp_model).cpu()
            try:
                robust_models[def_method] = copy.deepcopy(rst_model).cpu()
            except RuntimeError as e:
                temp_model = copy.deepcopy(copy_model1)
                temp_model.load_state_dict(IOtool.load(arch=arch, task=task, tag=def_method))
                robust_models[def_method] = copy.deepcopy(temp_model).cpu()
            ben_prob, _, _ = test_batch(copy_model, test_loader, device)
            normal_adv_prob, _, _ = test_batch(copy_model, adv_loader[method], device)
            robust_adv_prob, _, _ = test_batch(rst_model, adv_loader[method], device)
            normal_prob = IOtool.prob_scatter(ben_prob, normal_adv_prob)
            robust_prob = IOtool.prob_scatter(ben_prob, robust_adv_prob)
            result["AdvAttack"][method]['normal_scatter'] = normal_prob.tolist() 
            result["AdvAttack"][method]['robust_scatter'] = robust_prob.tolist() 
            test_acc = eval_test(rst_model, test_loader=test_loader, device=device)
            adv_test_acc = eval_test(rst_model, test_loader=adv_loader[method], device=device)
            logging.info(
                "[攻防推演阶段]鲁棒训练方法'{:s}'结束，模型准确率为：{:.3f}%，模型鲁棒性为：{:.3f}%".format(def_method, test_acc,
                                                                                     adv_test_acc))
            if (rate == 1.0):
                result["AdvTrain"]["def_acc"][str(method)] = adv_test_acc
                result["AdvTrain"]["def_asr"][str(method)] = 100.0 - adv_test_acc
                result["AdvAttack"][method]["def_asr"] = 100.0 - adv_test_acc
            tmp_path = osp.join(f"/model/ckpt/{task}_{arch}_{def_method}.pt")
            result["AdvTrain"]["rbst_model_path"][def_method] = tmp_path
            del copy_model
        adv_param[method]["eps"] = _eps
    logging.info("[模型测试阶段]【自动化攻防测试】算法运行结束")
    
    if "ENS" in defense_methods:
        result.update({"EnsembleDefense":{
            "ens_acc":{},
            "ens_asr":{},
        }})
        # 群智防御
        logging.info('[攻防推演阶段]即将执行【群智防御方法】算法，利用多智能体（每个鲁棒训练即是一种智能体）集成输出')
        ens_dataloader = adv_loader.copy()
        ens_model_list = list(robust_models.values())

        ens_model = ensemble_defense.run(model_list=ens_model_list)
        for method, ens_adv_loader in ens_dataloader.items():
            test_acc = eval_test(ens_model, test_loader=ens_adv_loader, device=device)
            result["EnsembleDefense"]["ens_acc"][method] = float(test_acc)
            result["EnsembleDefense"]["ens_asr"][method] = 100.0 - float(test_acc)
        logging.info("[模型测试阶段]【群智防御方法】算法运行结束")
    if 'Inte' in defense_methods:
        result.update({"InteDefense":{
            "Inte_acc":{},
            "Inte_asr":{},
        }})
        # 集成防御
        from function.ensemble.Integrated_defense.integrate import integrated_defense
        logging.info('[攻防推演阶段]即将执行【集成防御方法】算法，算法：Integrated Defense')
        data_size = 28 if channel == 1 else 32
        itr = 10 if channel == 1 else 30
        defend_info = integrated_defense(model = model, dataloader = test_loader, 
                                         attack_methods = adv_methods, adv_param = adv_param, 
                                         train_epoch = itr, in_channel=channel, 
                                         data_size=data_size, device=device, dataset=datasetparam['name'])
        print(defend_info)
        result['InteDefense']['ori'] = defend_info['ori_acc']
        for method in adv_methods:
            result['InteDefense']['Inte_acc'][method] = defend_info[method]['defend_rate']*100
            result['InteDefense']['Inte_asr'][method] = 100-defend_info[method]['defend_rate']*100
        logging.info("[模型测试阶段]【集成防御方法】算法运行结束")
    if 'Nash' in defense_methods:
        result.update({"game":{}})
        logging.info('[攻防推演阶段]训练完成共计{:d}个模型，开始攻防推演测试'.format(len(robust_models)))
        num_atk = len(adv_methods)
        robust_acc = np.zeros([num_atk, num_atk * 3])
        normal_acc = np.zeros([num_atk, num_atk * 3])
        logging.info('[攻防推演阶段]即将进行【攻防推演】算法，推演算法为纳什博弈算法')
        for i, atk_method in enumerate(adv_methods):
            adv_test_loader = adv_loader[atk_method]
            logging.info('[攻防推演阶段]使用对抗样本攻击算法{:s}生成的测试样本测试模型鲁棒性'.format(atk_method))
            for j, def_method in enumerate(robust_models.keys()):
                logging.info('[攻防推演阶段]测试模型鲁棒性：攻击算法为：{:s}，鲁棒性训练算法为：{:s}'.format(atk_method, def_method))
                _acc1 = eval_test(robust_models[def_method], test_loader=test_loader, device=device)
                _acc2 = eval_test(robust_models[def_method], test_loader=adv_test_loader, device=device)
                normal_acc[i, j] = _acc1
                robust_acc[i, j] = _acc2
                logging.info(
                    '[攻防推演阶段]测试模型鲁棒性，攻击算法为：{:s}，鲁棒性算法为：{:s}，正常准确率:{:.3f}，鲁棒性训练准确率为：{:.3f}'.format(
                        atk_method, def_method,
                        float(normal_acc[i, j]),
                        float(robust_acc[i, j])
                    )
                )

        result["game"]["methods"] = "nash"
        result["game"] = {
            "nash": {
                "atk_methods": list(adv_loader.keys()),
                "def_methods": list(robust_models.keys()),
                "normal_acc": normal_acc.tolist(),
                "robust_acc": robust_acc.tolist(),
                "def_profit": np.zeros([num_atk, 11]).tolist(),
                "def_strategy": {},
                "after_attack_acc": np.max(robust_acc, axis=1).tolist(),
                "defense_acc": []
            }
        }
        for m in adv_loader.keys():
            def_acc = round(100.0 - result["AdvAttack"]["atk_asr"][m], 2)
            result["game"]["nash"]["defense_acc"].append(def_acc)

        # nash game best choice, p = [0., 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1. ]
        logging.info('[攻防推演阶段]即将求解纳什博弈最优解，使用profit=p*acc+(1-p)*robust_acc计算最优情况')
        def_strategy = {}
        def_profit = np.zeros([num_atk, 11])
        atk_name = list(adv_loader.keys())
        def_name = list(robust_models.keys())
        for atk_idx in range(num_atk):
            best_profit = 0.0
            best_strategy = ""
            def_strategy[atk_name[atk_idx]] = []
            logging.info('[攻防推演阶段]正在进行纳什博弈推演，攻击者策略为：{:s}，计算防御者最优策略'.format(str(atk_name[atk_idx])))
            for idx, p in enumerate(np.arange(0, 1.1, 0.1)):
                for def_idx in range(3 * num_atk):
                    profit = p * normal_acc[atk_idx, def_idx] + (1.0 - p) * robust_acc[atk_idx, def_idx]
                    if profit > best_profit:
                        best_profit = profit
                        best_strategy = def_name[def_idx]
                def_profit[atk_idx, idx] = best_profit
                def_strategy[atk_name[atk_idx]].append(best_strategy)
            logging.info('[攻防推演阶段]完成攻击为{:s}的攻防推演，防御者最优策略分别为：{:s}'.format(str(atk_name[atk_idx]),
                                                                                str(def_strategy[atk_name[atk_idx]])))
        result["game"]["nash"]["def_strategy"] = def_strategy
        result["game"]["nash"]["def_profit"] = def_profit.tolist()
        logging.info('[攻防推演阶段]完成纳什博弈最优解求解，获得纳什博弈最优解')
        result["sys"]["report"] = {
            "robust": round(float(np.mean(robust_acc)), 2),
            "accuray": round(float(np.mean(normal_acc)), 2),
            "game": round(float(np.mean(def_profit)), 2),
            "speed": round(float(100.0), 2)
        }

        logging.info("[模型测试阶段]【攻防对抗推演】纳什博弈算法运行结束")
        logging.info('[攻防推演阶段] 完成攻防推演')
    
    result["stop"] = 1
    IOtool.write_json(result, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
        
def run_graph_knowledge(tid, stid, datasetparam, modelparam, auto_method, inputparam):
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    device = IOtool.get_device()
    logging = IOtool.get_logger(stid)
    batchsize = 128
    # 加载数据
    train_loader, test_loader, channel = load_dataset(datasetparam['name'], batchsize=batchsize)
    # 加载模型
    model = load_model_net(modelparam['name'], datasetparam['name'], channel=channel, logging=logging)
    import hashlib
    param_hash = hashlib.md5(str(inputparam).encode('utf8')).hexdigest()
    outpath = osp.join("output",tid,stid)
    result = {}
    if not osp.exists(outpath):
        os.mkdir(outpath)
    from function import adversarial_test
    if auto_method == "flow":
        # 加载
        adv_methods = inputparam["AdvMethods"]
        adv_param = {}
        for temp in adv_methods:
            adv_param.update({temp:inputparam[temp]})
        adv_loader = get_load_adv_data(datasetparam, modelparam, adv_methods, adv_param, model, test_loader, device, batchsize, logging=logging)
        temp = adversarial_test.run_adv_test(model,auto_method,dataloader=test_loader, attack_methods=adv_methods, param_hash=param_hash,
                              save_path=outpath, log_func=logging.info, device=device, adv_loader=adv_loader, )
        result[auto_method] = temp['result']
    elif auto_method in ["rule", "flow_rule"]:
        adv_methods = inputparam["AdvMethods"]
        temp = adversarial_test.run_adv_test(model, auto_method,dataloader=test_loader, attack_methods=adv_methods, param_hash=param_hash,
                              save_path=outpath, log_func=logging.info, device=device )
        result[auto_method] = temp['result']
    elif auto_method in ["graph", "graph_rule"]:
        temp = adversarial_test.run_adv_test(model, auto_method,dataloader=test_loader, param_hash=param_hash,
                              save_path=outpath, log_func=logging.info, device=device, attack_mode=inputparam['attack_mode'],
                              attack_type=inputparam['attack_type'],data_type=inputparam['data_type'],
                              defend_algorithm=inputparam['defend_algorithm'],task_type=inputparam["task_type"], dataset=datasetparam['name'].lower())
        result[auto_method] = temp
    # result = adversarial_test.run(model, test_loader, params = params, param_hash=str(time.time()),
    #                     log_func=logging.info)
    result["stop"] = 1
    IOtool.write_json(result, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)

def run_ensemble_defense(tid, stid, datasetparam, modelparam, adv_methods, adv_param, defense_methods):
    """群智化防御，包含PACA、博弈、集成等
    :params tid:主任务ID
    :params stid:子任务id
    :params datasetparam:数据集参数
    :params modelparam:模型参数
    :params adv_methods:list，对抗攻击方法
    :params adv_param:dict,对抗攻击参数
    :params defense_methods:list，集成防御方法
    """
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    device = IOtool.get_device()
    logging = IOtool.get_logger(stid)
    result={
        "AdvAttack":{
            "atk_acc":{},
            "atk_asr":{},
            },
        "AdvTrain":{
            "def_acc":{},
            "def_asr":{},
            "rbst_model_path":{}
        },
        "sys":{}
    }
    params = {
        "dataset": datasetparam,
        "model": modelparam,
        "out_path": osp.join(ROOT,"output", tid, stid),
        "device": torch.device(device),
        "adv_methods":{"methods":adv_methods},
        "root":ROOT,
        "stid":stid
    }
    robust_models = {}
    # 加载数据
    train_batchsize = 128  # 训练批大小
    test_batchsize = 128  # 测试批大小
    
    if datasetparam['name'].lower() == "mnist":
        transform = transforms.Compose([transforms.Resize(32), transforms.ToTensor(), transforms.Normalize([0.1307], [0.3081])])
        train_dataset = mnist.MNIST('./dataset/data/MNIST', train=True, transform=transform, download=True)
        test_dataset = mnist.MNIST('./dataset/data/MNIST', train=False, transform=transform, download=False)
    elif datasetparam['name'].lower() == "cifar10":
        print("cifar10")
        transform = transforms.Compose([transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip(),transforms.ToTensor(),transforms.Normalize(mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225])])
        # mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225]
        train_dataset = CIFAR10('./dataset/data/CIFAR10', train=True, transform=transform, download=True)
        test_dataset = CIFAR10('./dataset/data/CIFAR10', train=False, transform=transform, download=False)
    train_loader = DataLoader(train_dataset, batch_size=train_batchsize, shuffle=True,num_workers=2)
    test_loader = DataLoader(test_dataset, batch_size=test_batchsize,shuffle=False)
    # params["dataset"] = dataloader.__config__(dataset=datasetparam['name'].upper())
    # num_classes = train_loader.num_classes
    logging.info( "[数据集获取]：获取{:s}对抗样本已完成".format(datasetparam['name']))
    channel = 1 if datasetparam['name'].upper() == "MNIST" else 3
    # 加载模型
    model = modelparam["ckpt"]
    test_acc = {} # 样本准确率
    logging.info( "[加载被解释模型]：准备加载被解释模型{:s}".format(modelparam['name']))
    net = load_model_ex(modelparam['name'], datasetparam['name'], device, ROOT, reference_model=model, logging=logging)

    result["AdvAttack"]["test_acc"] = eval_test(net.eval().to(device), test_loader, device=device)
    logging.info("[模型训练阶段] 模型训练完成，测试准确率：{:.3f}% ".format(result["AdvAttack"]["test_acc"]))
    # net = net.eval().to(device)
    # 获取对抗样本
    adv_loader = {}
    # batchsize = get_batchsize(modelparam['name'], datasetparam['name'])
    for i, adv_method in enumerate(adv_methods):
        logging.info("[模型测试阶段] 正在运行对抗样本攻击:{:s}...[{:d}/{:d}]".format(adv_method, i + 1, len(adv_methods)))
        adv_loader[adv_method] = get_adv_loader(net.eval().to(device), test_loader, adv_method, params, batchsize=test_batchsize, logging=logging)
        result["AdvAttack"]["atk_acc"][adv_method] = eval_test(net.eval().to(device), adv_loader[adv_method], device=device)
        result["AdvAttack"]["atk_asr"][adv_method] = 100 - result["AdvAttack"]["atk_acc"][adv_method]
        logging.info("[模型测试阶段] {:s}对抗样本攻击运行结束，对抗样本测试准确率：{:.3f}% ".format(adv_method, result["AdvAttack"]["atk_acc"][adv_method]))

    copy_model1 = load_model_ex(modelparam['name'], datasetparam['name'], device, ROOT, reference_model=model, logging=logging)
    # paca
    if "PACA" in defense_methods:
        result.update({"PACA":{}})
        logging.info("[模型测试阶段] 即将运行【自动化攻击监测、算法加固】算法：paca_detect")
        
        result["PACA"]=paca_detect.run(model=copy_model1, test_loader=test_loader, adv_dataloader=adv_loader, params=params,
                        log_func=logging.info, channel=channel)
        logging.info("[模型测试阶段]【自动化攻击监测、算法加固】方法：paca_detect运行结束")
        logging.info('[软硬件协同安全攻防测试] 测试任务编号：{:s}'.format(tid))
        if len(defense_methods)==1:
            result['stop'] = 1
            IOtool.write_json(result, osp.join(ROOT,"output", tid, stid+"_result.json")) 
            IOtool.change_subtask_state(tid, stid, 2)
            IOtool.change_task_success_v2(tid)
            return
        else:
            defense_methods.remove("PACA")
    if "CAFD" in defense_methods:
        result.update({"CAFD":{
            "CAFD_acc":{},
            "CAFD_asr":{},
        }})
        from function.GroupDefense.CAFD.train_or_test_denoiser import cafd
        methods = ['fgsm', 'bim', 'rfgsm', 'cw', 'pgd', 'tpgd', 'mifgsm', 'autopgd', 'square', 'deepfool', 'difgsm']
        for method in adv_methods:
            method1 = method.lower()
            if method1 in methods:
                result["CAFD"]['CAFD_acc'][method] = cafd(target_model=copy_model1, dataloader=test_loader, method=method1, eps=1, channel=1, data_size=28, weight_adv=5e-3,
                weight_act=1e3, weight_weight=1e-3, lr=0.001, itr=10,
                batch_size=128, weight_decay=2e-4, print_freq=10, save_freq=2, device='cuda')
        if len(defense_methods)==1:
            result['stop'] = 1
            IOtool.write_json(result, osp.join(ROOT,"output", tid, stid+"_result.json")) 
            IOtool.change_subtask_state(tid, stid, 2)
            IOtool.change_task_success_v2(tid)
            return
        else:
            defense_methods.remove("CAFD")
    # if "Inte" in defense_methods:
    #     from function.GroupDefense.CAFD.train_or_test_denoiser import cafd
    # 对抗训练 & 攻防博弈
    logging.info('[攻防推演阶段]即将执行【自动化攻防测试】算法')
    logging.info('[攻防推演阶段]即将进行攻防推演，选择预设的{:d}种模型，调整参数并开始攻防推演'.format(len(adv_methods)))
    arch = modelparam['name']
    task = datasetparam['name']
    for i, method in enumerate(adv_methods):
        logging.info('[软硬件协同安全攻防测试] 测试任务编号：{:s}'.format(tid))
        logging.info('[攻防推演阶段]使用对抗样本算法{:s}生成的样本作为鲁棒训练数据，训练鲁棒性强的模型'.format(method))
        """专门针对上传的对抗样本设计，仅做测试不做鲁棒训练"""
        if "eps" not in adv_param[method].keys():
            adv_param[method]["eps"] = 0.1
        _eps = adv_param[method]["eps"]
        result["AdvAttack"][method] = {}
        for rate in [0.9, 1.0, 1.1]:
            adv_param[method]["eps"] = _eps * rate
            copy_model = copy.deepcopy(copy_model1)
            logging.info('[攻防推演阶段]使用对抗样本算法{:s}生成的样本作为鲁棒训练数据，eps参数为：{:.3f}'.format(method, float(
                adv_param[method]["eps"])))
            def_method = "{:s}_{:.5f}".format(method, adv_param[method]["eps"])
            
            cahce_weights = IOtool.load(arch=arch, task=task, tag=def_method)
            if cahce_weights is None:
                logging.info('[攻防推演阶段]缓存模型不存在，开始模型鲁棒训练（这步骤耗时较长）')
                logging.info('[软硬件协同安全攻防测试] 测试任务编号：{:s}'.format(tid))
                rst_model = robust_train(copy_model, train_loader, test_loader,
                                                     adv_loader=adv_loader[method], device=device,  epochs=10, method=method, adv_param=adv_param[method],
                                                     atk_method=method, def_method=def_method
                                                     )
                IOtool.save(model=rst_model, arch=arch, task=task, tag=def_method)
            else:
                logging.info('[攻防推演阶段]从默认文件夹载入缓存模型')
                temp_model = copy.deepcopy(copy_model1)
                temp_model.load_state_dict(cahce_weights)
                rst_model = copy.deepcopy(temp_model).cpu()
            try:
                robust_models[def_method] = copy.deepcopy(rst_model).cpu()
            except RuntimeError as e:
                temp_model = copy.deepcopy(copy_model1)
                temp_model.load_state_dict(IOtool.load(arch=arch, task=task, tag=def_method))
                robust_models[def_method] = copy.deepcopy(temp_model).cpu()
            ben_prob, _, _ = test_batch(copy_model, test_loader)
            normal_adv_prob, _, _ = test_batch(copy_model, adv_loader[method])
            robust_adv_prob, _, _ = test_batch(rst_model, adv_loader[method])
            normal_prob = IOtool.prob_scatter(ben_prob, normal_adv_prob)
            robust_prob = IOtool.prob_scatter(ben_prob, robust_adv_prob)
            result["AdvAttack"][method]['normal_scatter'] = normal_prob.tolist() 
            result["AdvAttack"][method]['robust_scatter'] = robust_prob.tolist() 
            test_acc = eval_test(rst_model, test_loader=test_loader, device=device)
            adv_test_acc = eval_test(rst_model, test_loader=adv_loader[method], device=device)
            logging.info(
                "[攻防推演阶段]鲁棒训练方法'{:s}'结束，模型准确率为：{:.3f}%，模型鲁棒性为：{:.3f}%".format(def_method, test_acc,
                                                                                     adv_test_acc))
            if (rate == 1.0):
                result["AdvTrain"]["def_acc"][str(method)] = adv_test_acc
                result["AdvTrain"]["def_asr"][str(method)] = 100.0 - adv_test_acc
                result["AdvAttack"][method]["def_asr"] = 100.0 - adv_test_acc
            tmp_path = osp.join(f"/model/ckpt/{task}_{arch}_{def_method}.pt")
            result["AdvTrain"]["rbst_model_path"][def_method] = tmp_path
            del copy_model
        adv_param[method]["eps"] = _eps
    logging.info("[模型测试阶段]【自动化攻防测试】算法运行结束")
    if "Inte" in defense_methods:
        result.update({"EnsembleDefense":{
            "ens_acc":{},
            "ens_asr":{},
        }})
        # 群智防御
        logging.info('[攻防推演阶段]即将执行【集成防御方法】算法，利用多智能体（每个鲁棒训练即是一种智能体）集成输出')
        ens_dataloader = adv_loader.copy()
        ens_model_list = list(robust_models.values())

        ens_model = ensemble_defense.run(model_list=ens_model_list, device=device)
        for method, ens_adv_loader in ens_dataloader.items():
            test_acc = eval_test(ens_model, test_loader=ens_adv_loader, device=device)
            result["EnsembleDefense"]["ens_acc"][method] = float(test_acc)
            result["EnsembleDefense"]["ens_asr"][method] = 100.0 - float(test_acc)
        logging.info("[模型测试阶段]【集成防御方法】算法运行结束")
    
    if "Nash" in defense_methods:
        result.update({"game":{}})
        logging.info('[攻防推演阶段]训练完成共计{:d}个模型，开始攻防推演测试'.format(len(robust_models)))
        num_atk = len(adv_methods)
        robust_acc = np.zeros([num_atk, num_atk * 3])
        normal_acc = np.zeros([num_atk, num_atk * 3])
        logging.info('[攻防推演阶段]即将进行【攻防推演】算法，推演算法为纳什博弈算法')
        for i, atk_method in enumerate(adv_methods):
            adv_test_loader = adv_loader[atk_method]
            logging.info('[攻防推演阶段]【指标5.1】使用对抗样本攻击算法{:s}生成的测试样本测试模型鲁棒性'.format(atk_method))
            for j, def_method in enumerate(robust_models.keys()):
                logging.info('[攻防推演阶段]【指标5.1】测试模型鲁棒性：攻击算法为：{:s}，鲁棒性训练算法为：{:s}'.format(atk_method, def_method))
                _acc1 = eval_test(robust_models[def_method], test_loader=test_loader, device=device)
                _acc2 = eval_test(robust_models[def_method], test_loader=adv_test_loader, device=device)
                normal_acc[i, j] = _acc1
                robust_acc[i, j] = _acc2
                logging.info(
                    '[攻防推演阶段]【指标5.1】测试模型鲁棒性，攻击算法为：{:s}，鲁棒性算法为：{:s}，正常准确率:{:.3f}，鲁棒性训练准确率为：{:.3f}'.format(
                        atk_method, def_method,
                        float(normal_acc[i, j]),
                        float(robust_acc[i, j])
                    )
                )

        result["game"]["methods"] = "nash"
        result["game"] = {
            "nash": {
                "atk_methods": list(adv_loader.keys()),
                "def_methods": list(robust_models.keys()),
                "normal_acc": normal_acc.tolist(),
                "robust_acc": robust_acc.tolist(),
                "def_profit": np.zeros([num_atk, 11]).tolist(),
                "def_strategy": {},
                "after_attack_acc": np.max(robust_acc, axis=1).tolist(),
                "defense_acc": []
            }
        }
        for m in adv_loader.keys():
            def_acc = round(100.0 - result["AdvAttack"]["atk_asr"][m], 2)
            result["game"]["nash"]["defense_acc"].append(def_acc)

        # nash game best choice, p = [0., 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1. ]
        logging.info('[攻防推演阶段]【指标5.1】即将求解纳什博弈最优解，使用profit=p*acc+(1-p)*robust_acc计算最优情况')
        def_strategy = {}
        def_profit = np.zeros([num_atk, 11])
        atk_name = list(adv_loader.keys())
        def_name = list(robust_models.keys())
        for atk_idx in range(num_atk):
            best_profit = 0.0
            best_strategy = ""
            def_strategy[atk_name[atk_idx]] = []
            logging.info('[攻防推演阶段]正在进行纳什博弈推演，攻击者策略为：{:s}，计算防御者最优策略'.format(str(atk_name[atk_idx])))
            for idx, p in enumerate(np.arange(0, 1.1, 0.1)):
                for def_idx in range(3 * num_atk):
                    profit = p * normal_acc[atk_idx, def_idx] + (1.0 - p) * robust_acc[atk_idx, def_idx]
                    if profit > best_profit:
                        best_profit = profit
                        best_strategy = def_name[def_idx]
                def_profit[atk_idx, idx] = best_profit
                def_strategy[atk_name[atk_idx]].append(best_strategy)
            logging.info('[攻防推演阶段]完成攻击为{:s}的攻防推演，防御者最优策略分别为：{:s}'.format(str(atk_name[atk_idx]),
                                                                                str(def_strategy[atk_name[atk_idx]])))
        result["game"]["nash"]["def_strategy"] = def_strategy
        result["game"]["nash"]["def_profit"] = def_profit.tolist()
        logging.info('[攻防推演阶段]完成纳什博弈最优解求解，获得纳什博弈最优解')
        result["sys"]["report"] = {
            "robust": round(float(np.mean(robust_acc)), 2),
            "accuray": round(float(np.mean(normal_acc)), 2),
            "game": round(float(np.mean(def_profit)), 2),
            "speed": round(float(100.0), 2)
        }

        logging.info("[模型测试阶段]【攻防对抗推演】纳什博弈算法运行结束")
        logging.info('[攻防推演阶段] 完成攻防推演')
    
    result["stop"] = 1
    IOtool.write_json(result, osp.join(ROOT,"output", tid, stid+"_result.json")) 
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)

def run_advtraining_at(tid,AAtid, dataset, modelname, attackmethod, evaluate_methods):
    """CNN对抗训练
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params modelname：模型类型
    :params adv_method：对抗训练算法
    :params evaluate_methodss：攻击方法
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    device = IOtool.get_device()
    # device = torch.device('cuda' if torch.cuda.is_available() else 'cpu' )
    logging = IOtool.get_logger(AAtid)
    
    # 预处理数据，保持格式一致
    batch_size = 32
    datasetparam = {}
    modelparam = {}
    adv_param = {'FGSM': {'eps': 0.031, 'norm': '1'}, 'FFGSM': {}, 'RFGSM': {}, 'MIFGSM': {}, 'BIM': {'eps': 0.031, 'eps_step': 0.01, 'max_iter': 20, 'norm': 'inf'}, 'PGDL1': {'eps': 0.3, 'eps_step': 0.1, 'max_iter': 20, 'num_random_init': 1}, 'PGDL2': {'eps': 0.3, 'eps_step': 0.1, 'max_iter': 20, 'num_random_init': 1}, 'DIFGSM': {}, 'C&W': {'max_iterations': 1000, 'lr': 0.01}, 'TPGD': {}}
    result = {
        "Normal": {
            "atk_acc":{},
            "atk_asr":{},
            },
        "Enhance":{
            "atk_acc":{},
            "atk_asr":{},
        }
    }
    
    datasetparam["name"] = dataset
    modelparam["name"] = modelname
    # CNN对抗训练
    # 加载数据
    logging.info('[对抗鲁棒性训练]正在加载数据{:s}'.format(dataset))
    train_loader, test_loader, channel = load_dataset(dataset, batchsize=batch_size)
    # 训练/加载Normal模型
    logging.info('[对抗鲁棒性训练]正在加载模型{:s}'.format(modelname))
    model = load_model_net(modelname, dataset, channel=channel, logging=logging)
    # Normal模型对抗攻击
    logging.info('[对抗鲁棒性训练]即将进行模型对抗测试')
    all_atk = evaluate_methods
    if attackmethod not in evaluate_methods:
        all_atk.append(attackmethod)
    adv_loader = get_load_adv_data(datasetparam, modelparam, all_atk, adv_param, model, test_loader, device, batch_size, logging=logging)
    for i, method in enumerate(evaluate_methods):
        result["Normal"]["atk_acc"][method] = eval_test(model.eval().to(device), adv_loader[method], device=device)
        result["Normal"]["atk_asr"][method] = 100 - result["Normal"]["atk_acc"][method]
        logging.info("[对抗鲁棒性训练] {:s}对抗样本测试准确率：{:.3f}% ".format(method, result["Normal"]["atk_acc"][method]))
    # 训练/加载Enhance模型
    logging.info('[对抗鲁棒性训练]正在加载鲁棒训练模型{:s}'.format(modelname))
    copy_model = copy.deepcopy(model)
    if "eps" not in adv_param[attackmethod].keys():
        adv_param[attackmethod]["eps"] = 1
    logging.info('[对抗鲁棒性训练]使用对抗样本算法{:s}生成的样本作为鲁棒训练数据，eps参数为：{:.3f}'.format(attackmethod, float(adv_param[attackmethod]["eps"])))
    def_method = "{:s}_{:.5f}".format(attackmethod, adv_param[attackmethod]["eps"])
    cahce_weights = IOtool.load(arch=modelname, task=dataset, tag=def_method)
    if cahce_weights is None:
        logging.info('[对抗鲁棒性训练]缓存模型不存在，开始模型鲁棒训练（这步骤耗时较长）')
        logging.info('[对抗鲁棒性训练] 测试任务编号：{:s}'.format(tid))
        attack = Attack_Obj(dataset_name = datasetparam['name'], model = model, dataloader = test_loader, device = device, method= attackmethod, attackparam=adv_param[attackmethod])
        rst_model = robust_train(copy_model, train_loader, test_loader,
                    adv_loader=adv_loader[attackmethod], attack=attack, device=device,  epochs=10, method=attackmethod, adv_param=adv_param[attackmethod],
                    atk_method=attackmethod, def_method=def_method
                                                )
        IOtool.save(model=rst_model, arch=modelname, task=dataset, tag=def_method)
    else:
        logging.info('[对抗鲁棒性训练]从默认文件夹载入缓存模型')
        temp_model = copy.deepcopy(copy_model)
        temp_model.load_state_dict(cahce_weights)
        rst_model = copy.deepcopy(temp_model).cpu()
    try:
        robust_models = copy.deepcopy(rst_model).cpu()
    except RuntimeError as e:
        temp_model = copy.deepcopy(copy_model)
        temp_model.load_state_dict(IOtool.load(arch=modelname, task=dataset, tag=def_method))
        robust_models = copy.deepcopy(temp_model).cpu()
    
    # Enhance模型对抗攻击
    test_acc = eval_test(rst_model, test_loader=test_loader, device=device)
    for i, method in enumerate(evaluate_methods):
        result["Enhance"]["atk_acc"][method] = eval_test(rst_model, adv_loader[method], device=device)
        result["Enhance"]["atk_asr"][method] = 100 - result["Enhance"]["atk_acc"][method]
        logging.info("[对抗鲁棒性训练] {:s}对抗样本测试准确率：{:.3f}% ".format(method, result["Normal"]["atk_acc"][method]))
        # adv_test_acc = eval_test(rst_model, test_loader=adv_loader[adv_method], device=device)
        logging.info(
        "[对抗鲁棒性训练]鲁棒训练方法'{:s}'结束，模型准确率为：{:.3f}%，模型鲁棒性为：{:.3f}%".format(def_method, test_acc,
                                                                                result["Enhance"]["atk_acc"][method]))
    
    tmp_path = osp.join(f"/model/ckpt/{dataset}_{modelname}_{def_method}.pt")
    result["Enhance"]["rbst_model_path"]= tmp_path
    
    result["stop"] = 1
    IOtool.write_json(result,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)
    

def run_advtraining_gnn(tid,AAtid, dataset, batch_size, train_size, test_size, val_size, n_iters, train_Q, margin_iters, q_ratio, burn_in, random_state):
    """图神经网络鲁棒训练
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params batch_size: 批处理大小
    :params train_size：训练集比例
    :params test_size：测试集比例
    :params val_size：验证集比例
    :params n_iters：训练迭代的次数
    :params train_Q：全局扰动数量
    :params margin_iters：
    :params q_ratio：属性扰动数量
    :params burn_in:未优化鲁棒损失的迭代次数
    :params random_state：随机数生成器使用的种子
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    # devive = IOtool.get_device()
    logging = IOtool.get_logger(AAtid)
    res = robust_gnn.run_robust_gcn(
        dataset_name=dataset.lower(),  # 数据集
        train_Q=train_Q,  # 全局允许扰动的数量。
        batch_size=batch_size,  # 一次训练所选取的样本数
        q_ratio=q_ratio,  # 属性扰动数量
        train_size=train_size,  # 分割中包含的数据集的比例
        val_size=val_size,  # 验证分割中包含的数据集的比例。
        test_size=test_size,  # 测试分割中包含的数据集的比例
        random_state=123,  # 随机数生成器使用的种子
        n_iters=n_iters,  # 训练迭代的次数。
        burn_in=burn_in,  # 开始时未优化鲁棒损失的迭代次数。
        margin_iters=margin_iters, path=osp.join(ROOT,"output", tid, AAtid), logger_func=logging.info)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_featurescatter(tid,AAtid, dataset, modelname, attack_method, evaluate_methods, lr, batch_size, max_epoch, decay_epoch, decay_rate):
    """特征散射鲁棒训练
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params modelname：模型类型
    :params lr：学习率
    :params batch_size: 批处理大小
    :params max_epoch：最大训练轮数
    :params decay_epoch：学习率衰减的轮数
    :params decay_rate：学习率衰减的速率
    :params weight_decay：权重衰减
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    # devive = IOtool.get_device()
    logging = IOtool.get_logger(AAtid)
    res = adv_traind.run_featurescatter(
        dataset=dataset.lower(),  # 数据集
        modelname=modelname.lower(),  # 模型类型
        attack_method = attack_method, # 对抗训练方法
        evaluate_methods = evaluate_methods, # 评估算法
        lr = lr, # 学习率
        batch_size=batch_size,  # 批处理大小
        max_epoch=max_epoch,  # 最大训练轮数
        decay_epoch=decay_epoch,  # 学习率衰减的轮数
        decay_rate=decay_rate,  # 学习率衰减的速率
        out_path=osp.join(ROOT,"output", tid, AAtid), logging=logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)

def run_seat(tid,AAtid, dataset, modelname, lr, epsilon, max_epoch, evaluate_method):
    """特征散射鲁棒训练
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params modelname：模型类型
    :params lr：学习率
    :params n_class: 分类类别数
    :params max_epoch：最大训练轮数
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    # devive = IOtool.get_device()
    logging = IOtool.get_logger(AAtid)
    res = adv_traind.run_seat(
        dataset = dataset,
        modelname=modelname,  
        lr = lr, 
        epsilon=epsilon,  
        max_epoch = max_epoch,
        evaluate_method = evaluate_method,
        out_path=osp.join(ROOT,"output", tid, AAtid), 
        # out_path=osp.join(ROOT,"output", tid, "S20231127_1552_b9dabb5"), 
        logging=logging)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)
   
def run_rift(tid, AAtid, dataset, model, attack_method, evaluate_methods, train_epoch, at_epoch, batchsize):
    """关键参数微调鲁棒训练
    :params tid:主任务ID
    :params AAtid:子任务id
    :params dataset: 数据集名称
    :params modelname：模型类型
    :params attack_method：对抗训练方法
    :params evaluate_methods: 测试攻击方法list
    :params max_epoch：最大训练轮数
    :output res:需保存到子任务json中的返回结果/路径
    """
    IOtool.change_subtask_state(tid, AAtid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, AAtid, time.time())
    device = IOtool.get_device()
    logging = IOtool.get_logger(AAtid)
    res = adv_traind.run_rift(dataset, model, attack_method, evaluate_methods,  train_epoch, at_epoch, batchsize, out_path=osp.join(ROOT,"output", tid, AAtid), logging=logging, device=device)  
    res["stop"] = 1
    IOtool.write_json(res,osp.join(ROOT,"output", tid, AAtid+"_result.json"))
    IOtool.change_subtask_state(tid, AAtid, 2)
    IOtool.change_task_success_v2(tid=tid)
    
import csv
def llm_attack(tid, stid, goal, target):
    IOtool.change_subtask_state(tid, stid, 1)
    IOtool.change_task_state(tid, 1)
    IOtool.set_task_starttime(tid, stid, time.time())
    logging = IOtool.get_logger(stid)
    logpath = osp.join(ROOT, "output" , tid, stid+"_log.txt")
    logging.info("start LLM attack... ")
    logging.info("input goal and target... ")
    filename = "function/attack/llm-attacks/data/advbench/harmful_behaviors.csv"
    with open(filename, 'w') as csv_fp:
        writer = csv.writer(csv_fp)
        writer.writerow(['goal','target'])
        writer.writerow([goal,target])
    os.system("bash -c 'source ~/anaconda3/etc/profile.d/conda.sh && conda activate gpt && cd function/attack/llm-attacks/experiments/launch_scripts && bash run_gcg_individual.sh vicuna behaviors >> "+ logpath+"'")
    logging.info("end LLM attack... ")
    os.system("bash -c 'source ~/anaconda3/etc/profile.d/conda.sh && conda deactivate'")
    resp = IOtool.load_json(osp.join("function/attack/llm-attacks/experiments/results","individual_behaviors_vicuna_gcg_offset0.json"))
    resp2 = IOtool.load_json("function/attack/llm-attacks/experiments/launch_scripts/params.json")
    resp["LLMparams"] = resp2["LLMparams"]
    resp['stop'] = 1
    IOtool.write_json(resp, osp.join(ROOT,"output", tid, stid+"_result.json"))
    IOtool.change_subtask_state(tid, stid, 2)
    IOtool.change_task_success_v2(tid)
    logging.info("end LLM attack... ")
    return resp
def zipDir(dirpath, outFullName):
    """
    压缩指定文件夹
    :param dirpath: 目标文件夹路径
    :param outFullName: 压缩文件保存路径+xxxx.zip
    :return: 无
    """
    import zipfile
    zip = zipfile.ZipFile(outFullName, "w", zipfile.ZIP_DEFLATED)
    for path, dirnames, filenames in os.walk(dirpath):
        # 去掉目标跟路径，只对目标文件夹下边的文件及文件夹进行压缩
        fpath = path.replace(dirpath, '')
 
        for filename in filenames:
            zip.write(os.path.join(path, filename), os.path.join(fpath, filename))
    zip.close()