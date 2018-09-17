import numpy as np
from math import log
# 控制回撤，进场时机，大盘
# 大盘跌破20日均线，且跌幅超过2.9% 。
# 大盘跳空低开且跌破20日均线。
# 这两种都强制空仓
# 下次入场时机，个股必须站上20日线
# 手动排除列表

#2015年6月1日 2017年2月10日
# 止损改实时
# 添加盘前三黑鸦止损 和 28止损 

# 123% 回撤15% 16-2-24 ~ 17-1-9


MY_EXCLUDE_STOCKS = ["600656.XSHG","000594.XSHE","300372.XSHE","300354.XSHE","000856.XSHE" ,"000609.XSHE"]

# set parameters，一次启动出现一次init内容，开始策略，第二天不会再动这个
def init(context):
    # context 是字典，我们可以向其中添加东西
    # 这个是大盘指标
    context.index = "000001.XSHG"
    context.small_cap_num = 50
 
    # 第一套当日清仓方案 单日下跌幅度超过-4.3% 且跌破20日线 要卖出，这个数值很重要
    context.stop_index_dropone = -0.043
    
    # 第一套次日清仓方案，在前一日清仓后，因为跌停没有卖出的，今日再次清仓。这个要求次日跌幅也超过-4.3%，如果没有超过，一样不会清仓。尝试使用过-2.8% ，效果不好。最终还是这个数值。
    context.stop_index_droptwo = -0.043

   # 第二套清仓方案 大盘单日跌幅超过-6.8% 要卖出
    context.stop_index_drop = -0.068

    context.win_length = 160
    
   # 超跌买入阈值，还需要测试最佳阈值，0.6 ->5.7577
   # 这个阈值非常重要 玄铁剑 6 熊市中6更好，牛市中5更好
    context.rel_return = -0.6
    
    #这里是仓位 最大仓位 0.3 ~ 0.37
    #非常重要。仓位大小与市场牛熊有关，牛市仓位高，赚越多。熊市仓位少越平衡回撤
    # 0.3 回撤更有效,盈利空间也比 0.37 高。确定使用0.3。
    
    context.max_weight = 0.3
    
    # 单个股票最大仓位，控制回撤非常有效，同时不影响收益
    
    # schedule rebalance function，每天开市 80 分钟 ，非常重要的参数
    context.reblancetime = 230
    
    #context.reblancetime = 212
    scheduler.run_daily(rebalance, time_rule = market_open(0,context.reblancetime))
    #scheduler.run_weekly(rebalance, 3)


# 在交易之前，选择市值最小的个股
def before_trading(context):
    # 选择市值最小的xx个股票，这里没有市盈率的要求,但是对盈利有要求，盈利超过5000万
    fundamental_df = get_fundamentals(
        query(
            fundamentals.income_statement.revenue
            )
            .filter( fundamentals.income_statement.revenue > 0 )
            .order_by( fundamentals.eod_derivative_indicator.market_cap.asc() )
            .limit( context.small_cap_num )
            )
    context.stocks = fundamental_df.columns.values
    # 排除ST股
    context.stocks = remove_st(context.stocks)
    # 加入
    update_universe(context.stocks)
    
    
def handle_bar(context, bar_dict):
    pass  


# open/close orders  在平衡过程中 开启和关闭订单 
# 这里是把bar_dic 与 context 混合在一起了。
def rebalance(context, bar_dict):
    # close stock positions not in the current universe
    # 把当前持仓的股票，但不在今日候选列表中的做卖出处理
    for stock in context.portfolio.positions.keys():
        if stock not in context.stocks:
            order_target_percent(stock, 0); trade_log(stock, 0)
    
    # close all positions when index drops by stop_index_drop
    # 如前一个交易日跌幅超过5.7%，则全部卖出


# 这里把 hist 定位到了index 上证指数，也就是  context.index = "000001.XSHG"
# 0 1 2 三个交易日 5日 才出现信号
# 0 1   两个交易日 4日 就出现信号
# 当前最新的才是今天，3个情况下2 是今天。2个情况下1 是今天。
    #index_hist = history_bars(context.index,3,'1d','close')
    index_hist = history(3, "1d", "close")[context.index] # 前3个交易日的指数 index是上证指数
    index_return_1d = log(index_hist[2]/index_hist[1]) # log(昨日指数/前日指数)4号清仓信号
    index_return_2d = log(index_hist[1]/index_hist[0]) # 昨天 5号清仓信号，暴跌后第二天清仓信号
# 得到上证指数下跌指数  context.stop_index_drop = -0.043 ，
# ---------------------制作了一次空仓与二次空仓-----------------------------------------------
#   如果下跌幅度高于 4.3% 且 数值小于20MA ，那么清仓
#   一次清仓条件是当日跌幅超过4.3%
    con1 = index_return_1d < context.stop_index_dropone
    
#   二次清仓条件是当日跌幅超过2.8%，其次是前一天跌停的股，第二天清仓，写了后效果不好。最终都使用了4.3%，想要高盈利，也需要必要的回撤，本身也是超跌思路来做。必要回撤不可避免。
    # 
    con2 = index_return_2d < context.stop_index_droptwo
    
    indexma5 = bar_dict[context.index].mavg(5,frequency = 'day')
    indexma20 = bar_dict[context.index].mavg(20,frequency = 'day')
    
    
    macondiction = indexma5 < indexma20
    
#   指的是第二天，第二天跌停的，开始了，这个是大盘数据，不是个股数据，所以不存在把那支股清仓的情况。设定阈值为 -4.3% 所以这个-2.8% 就无法清仓。
    if con2 and macondiction:
        logger.info("[ %s],%.2f,%.2f" % ("-------------二次空仓1------",indexma5,indexma20))
        # 这里是stock 是数字 600360xts
        for stock in context.stocks: #卖出全部股票
               order_target_percent(stock, 0); trade_log(stock, 0)
        return
    
#   指的是当天空仓，第一天空仓，还有跌停的    
    if con1 and macondiction:
        logger.info("[ %s],%.2f,%.2f" % ("-------------空仓策略1------",indexma5,indexma20))
        for stock in context.stocks: #卖出全部股票
            order_target_percent(stock, 0); trade_log(stock, 0)
        return
    
  
# -----------------------------------------------------------------------------------------
# --------有一个问题，前一天发出空仓策略的，没有清理的第二天空仓，如何做呢。
# -----------------------------------------------------------------------------------------   
#   如果下跌幅度高于 5.7% ，那么清仓
    if index_return_1d < context.stop_index_drop: # -0.043对应5.7%的下跌
        logger.info("[ %s],%.4f,%.4f" % ("----------------------空仓策略2---------------------------",index_return_1d,context.stop_index_drop))
        for stock in context.stocks: #卖出全部股票
            order_target_percent(stock, 0); trade_log(stock, 0)
        return
# -----------------------------------------------------------------------------------------
    # narrow down stock universe: not in suspension + relative strength < -0.5
    
    
    # 160天以来，所有股票相对上证的涨跌幅度，所以这个是数组，
    stock_hist = history(context.win_length, "1d", "close")
    # 过去N天每个股票的回调幅度 -0.03表示跌了3%
    stock_return = (stock_hist.ix[context.win_length-1]-stock_hist.ix[0])/stock_hist.ix[0] 
    # 过去N天上证的回调幅度
    index_return = stock_return[context.index] 
    # 相对强度，正数表示股票表现较强，负数表示表现弱
    rel_return = stock_return - index_return
    
    # 遍历所有候选池子，要求
    # 1. 股票可以交易
    # 2. 股票没有涨停跌停
    # 3. 此股票的回调差 < 上证回调差绝对值的-0.5倍，说明股票超跌
    # 
    # 这里有两个方案：
    # 4.1 个股5日线突破20日线买入
    #   bar_dict[stock].mavg(5,frequency = 'day') > bar_dict[stock].mavg(20,frequency = 'day')
    # 4.2 大盘5日线突破20日线买入
    #   indexma5 > indexma20
    # 最终都没用。显然，必要回撤不可避免。添加太多限制，导致策略更不好。
    # 具体落实到个股
    context.stocks = [stock for stock in context.stocks 
    if bar_dict[stock].is_trading 
    and bar_dict[stock].open< 1.095*stock_hist[stock].iloc[-1] 
    and bar_dict[stock].open> 0.905*stock_hist[stock].iloc[-1] 
    and rel_return[stock]<abs(index_return)*context.rel_return]
    
    # 控制回撤极其有效，故而考虑周期替换。
    #and bar_dict[stock].mavg(5,frequency = 'day') > bar_dict[stock].mavg(20,frequency = 'day')]
    # and indexma5 > indexma20]
    # place equally weighted orders
    if len(context.stocks) == 0:
            logger.info("备选股数为零，不进行调仓")
            return
    
    ########################
    # 超跌越多，权重越大，最大30%， 最小0%
    # 对应超跌幅度最大是1.5倍上证，最小0.5倍上证
    weight = {} # 保存每个股票的超跌幅度作为权重
    sum_weight = 0 # 所有超跌幅度求和，为后续归一化准备
    for stock in context.stocks:
        weight[stock] = abs((rel_return[stock]-abs(index_return)*context.rel_return)/(index_return) ) * context.max_weight # 超跌的相对情况
        if weight[stock] > context.max_weight: # 避免过大，对应超跌幅度最大是1.5倍上证，最小0.5倍上证
            weight[stock] = context.max_weight
        sum_weight += weight[stock]
        
    for stock in context.stocks:
        weight[stock] /= sum_weight # 归一化
        if weight[stock] > context.max_weight: # 单个股票仓位控制
            weight[stock] = context.max_weight
        trade_log(stock, weight[stock])
        order_target_percent(stock, weight[stock]) 
        
    ########################
    ###weight = 1.0/len(context.stocks)
    #### 单个股票仓位不能超过30%
    ###if weight > context.max_weight:
    ###    weight = context.max_weight
    ###for stock in context.stocks:
    ###    order_target_percent(stock, weight); trade_log(stock, weight)
    
    
# handle data 每分钟执行一次，我们要的是这个而不是全部只执行一次，做不到实时的监控
# 所以函数这样写，是完全错误的。

# 有bar_dict就可以发送订单信号
# 从有订单开始就做了


def after_trading(context):
    pass
# Utils -------------------is_st_st
#--------以下是函数----------------------------------------------------
def is_3_black_crows(stock):
    # 三只乌鸦说明来自百度百科
    # 1. 连续出现三根阴线，每天的收盘价均低于上一日的收盘
    # 2. 三根阴线前一天的市场趋势应该为上涨
    # 算法
    # 有效三只乌鸦描述众说纷纭，这里放宽条件，只考虑1和2
    # 根据前4日数据判断
    h_c = history_bars(stock, 4, '1d','close')
    h_o = history_bars(stock, 4, '1d','open')
    h_close = list(h_c)
    h_open = list(h_o)

    if len(h_close) < 4 or len(h_open) < 4:
        return False
    
    # 一阳三阴
    if h_close[-4] > h_open[-4] \
        and (h_close[-1] < h_open[-1] and h_close[-2]< h_open[-2] and h_close[-3] < h_open[-3]):
        return True
    return False

# 获取股票20日以来涨幅，根据当前价计算
# n 默认20日
def get_growth_rate(security, n=20):
    # 20天前的数据，20天为0
    lc = get_close_price(security, n)
    #c = data[security].close
    # 前1天，开盘1分钟的数据
    c = get_close_price(security, 1, '1m')
    if not np.isnan(lc) and not np.isnan(c) and lc != 0:
        temp = (c - lc) / lc
        return temp
    else:
        logger.info("数据非法, security: %s, %d日收盘价: %f, 当前价: %f" %(security, n, lc, c))
        return 0

# 获取前n个单位时间当时的收盘价
def get_close_price(security, n, unit='1d'):
    return history_bars(security, n, unit, 'close')[0]

    
# Utils -------------------is_st_st
# 移除ST股票(提升收益2%)
def remove_st(stocks):
    result = []
    for s in stocks:
        if (not is_st_stock(s)) and (s not in MY_EXCLUDE_STOCKS):
            result.append(s)
    return np.array(result)

# 交易日志
def trade_log(stock, weight):
    logger.info("[ %s(%s) -> %.2f]" % (stock_name(stock), stock, weight))

# 股票名字
def stock_name(stock):
    return instruments(stock).symbol



