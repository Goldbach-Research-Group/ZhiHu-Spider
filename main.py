import spider

sp = spider.ZhiHuSpider()
if sp.isLogin():
    print('您已经登录')
else:
    account = input('输入账号：')
    secret = input('输入密码：')
    sp.login(account, secret)
sp.getQsAnswer('306537777')