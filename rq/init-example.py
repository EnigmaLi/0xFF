def init(context):
    context.s1 = "000001.XSHE"
    logger.info("Interested at stock: " + str(context.s1))

def before_trading(context, bar_dict):
    pass


def handle_bar(context, bar_dict):
    # order_shares(context.s1, 1000)
    pass

