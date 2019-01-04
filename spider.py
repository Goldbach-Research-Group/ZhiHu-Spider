import time
import re
import requests
import http.cookiejar
from PIL import Image
import json
from bs4 import BeautifulSoup

def writeFile(filePath, content):
    print('Write info to file:Start...')
    # 将文件内容写到文件中
    with open(filePath, 'a', encoding='utf-8') as f:
        f.write(content)
        print('Write info to file:end...')

def catchBan(tryFun):
    ajson, ansResponse = tryFun()
    if "error" in ajson:
        print("Error!")
        return tryFun()
    else:
        return ajson, ansResponse

class ZhiHuSpider(object):
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 '
                                      '(KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36',
                        "Host": "www.zhihu.com",
                        "Referer": "https://www.zhihu.com/",
                        }
        # 建立一个会话，可以把同一用户的不同请求联系起来；直到会话结束都会自动处理cookies
        self.session = requests.Session()
        self.session.keep_alive = False
        # 建立LWPCookieJar实例，可以存Set-Cookie3类型的文件。
        # 而MozillaCookieJar类是存为'/.txt'格式的文件
        self.session.cookies = http.cookiejar.LWPCookieJar("cookie")
        # 若本地有cookie则不用再post数据了
        try:
            self.session.cookies.load(ignore_discard=True)
            print('Cookie加载成功！')
        except IOError:
            print('Cookie未加载！')
        self.dr = re.compile(r'<[^>]+>', re.S) # 去除HTML提取回答生成摘要用的正则
        self.resetPar() # 关于爬取参数的初始化


    def resetPar(self):
        # 每次取的回答数
        self.limit = 20
        # 获取答案时的偏移量
        self.offset = 0
        # 开始时假设当前有这么多的回答，得到请求后我再解析
        self.total = 1
        # 我们当前已记录的回答数量
        self.record_num = 0


    def get_xsrf(self): # 获取参数_xsrf
        response = self.session.get('https://www.zhihu.com', headers=self.headers)
        html = response.text
        get_xsrf_pattern = re.compile(r'<input type="hidden" name="_xsrf" value="(.*?)"')
        _xsrf = re.findall(get_xsrf_pattern, html)[0]

        return _xsrf


    def get_captcha(self):
        """
        获取验证码本地显示
        返回你输入的验证码
        """
        t = str(int(time.time() * 1000))
        captcha_url = 'http://www.zhihu.com/captcha.gif?r=' + t + "&type=login"
        response = self.session.get(captcha_url, headers=self.headers)
        with open('cptcha.gif', 'wb') as f:
            f.write(response.content)
        # Pillow显示验证码
        im = Image.open('cptcha.gif')
        im.show()
        captcha = input('本次登录需要输入验证码： ')
        return captcha


    def login(self, username, password): # 输入自己的账号密码，模拟登录知乎
        # 检测到11位数字则是手机登录
        if re.match(r'\d{11}$', username):
            url = 'http://www.zhihu.com/login/phone_num'
            data = { # '_xsrf': self.get_xsrf(),
                    'password': password,
                    'remember_me': 'true',
                    'phone_num': username
                    }
        else:
            url = 'https://www.zhihu.com/login/email'
            data = { # '_xsrf': self.get_xsrf(),
                    'password': password,
                    'remember_me': 'true',
                    'email': username
                    }
        result = self.session.post(url, data=data, headers=self.headers)
        # 读验证码这块不对，先删掉了
        '''
        # 打印返回的响应，r = 1代表响应失败，msg里是失败的原因
        # loads可以反序列化内置数据类型，而load可以从文件读取
        if json.loads(result.text)["r"] == 1:
            # 要用验证码，post后登录
            data['captcha'] = self.get_captcha()
            result = self.session.post(url, data=data, headers=self.headers)
            print((json.loads(result.text))['msg'])
        '''
        # 保存cookie到本地
        self.session.cookies.save(ignore_discard=True, ignore_expires=True)


    def isLogin(self):
        # 通过查看用户个人信息来判断是否已经登录
        url = "https://www.zhihu.com/settings/profile"
        # 禁止重定向，否则登录失败重定向到首页也是响应200
        login_code = self.session.get(url, headers=self.headers, allow_redirects=False,verify=False).status_code
        if login_code == 200:
            return True
        else:
            return False

    def getAnswerUrl(self, questionId):
        # URL：https://www.zhihu.com/api/v4/questions/39162814/answers?sort_by=default&include=data[*].is_normal,content&
        # limit=20&offset=0
        return 'https://www.zhihu.com/api/v4/questions/' + \
                questionId + '/answers' \
                '?sort_by=default&include=data[*].is_normal,voteup_count,content' \
                '&limit=' + str(self.limit) + '&offset=' + str(self.offset)

    def getActivitiesUrl(self,userId):
        # activitiesUrl: https://www.zhihu.com/api/v4/members/yu-ye/activities?per_page=20&include=data%5B%2A%5D.answer_count%2Carticles_count%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics&
        # limit=20&offset=0
        return 'https://www.zhihu.com/api/v4/members/' + \
                userId + '/activities?per_page=20&include=data%5B%2A%5D.answer_count%2Carticles_count%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics&' + \
                'limit=' + str(self.limit) + '&offset=' + str(self.offset)

    def getAnswersUrl(self,userId):
        # answersUrl: https://www.zhihu.com/api/v4/members/yu-ye/answers?per_page=20&include=data%5B%2A%5D.answer_count%2Carticles_count%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics&
        # limit=20&offset=0
        return 'https://www.zhihu.com/api/v4/members/' + \
                userId + '/answers?per_page=20&include=data%5B%2A%5D.answer_count%2Carticles_count%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics&' + \
                'limit=' + str(self.limit) + '&offset=' + str(self.offset)

    def getFollowerUrl(self,userId):
        # followerUrl: https://www.zhihu.com/api/v4/members/yu-ye/followers?
        # per_page=20
        # &include=data%5B%2A%5D.answer_count%2Carticles_count%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics&
        # limit=20&offset=0
        return 'https://www.zhihu.com/api/v4/members/' + \
                userId + '/followers?per_page=' + str(self.limit) + \
                '&include=data%5B%2A%5D.answer_count%2Carticles_count%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics&' + \
                'limit=' + str(self.limit) + '&offset=' + str(self.offset)

    def getFolloweeUrl(self,userId):
        # followeeUrl: https://www.zhihu.com/api/v4/members/yu-ye/followees?include=data%5B%2A%5D.answer_count%2Carticles_count%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics&
        # limit=20&offset=0
        followeeUrl = 'https://www.zhihu.com/api/v4/members/' + \
                      userId + '/followees?include=data%5B%2A%5D.answer_count%2Carticles_count%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics&' + \
                      'limit=' + str(self.limit) + '&offset=' + str(self.offset)

    def getUserName(self, userId): # 获取用户信息，还没用上
        url = 'https://www.zhihu.com/people/' + userId + '/activities'
        response = self.session.get(url, headers=self.headers)
        print(response.content)
        soup = BeautifulSoup(response.content, 'lxml')
        name = soup.find_all('span', {'class': 'ProfileHeader-name'})[0].string
        return name

    def getAllFollower(self,userId, getFollowerContent=False):
        follower_info = []
        print('Fetch info start...')

        while self.record_num < self.total:
            url = self.getFollowerUrl(userId)
            def tryFun():
                response = self.session.get(url, headers=self.headers)
                ajson = json.loads(response.content)
                return ajson,response
            ajson, response = catchBan(tryFun)
            writeFile(userId + '-' + str(self.record_num) + '.json', response.content.decode())  # 把信息存下来
            self.total = ajson['paging']['totals']  # 粉丝总数
            isEnd = self.getFollower(ajson['data'], follower_info, getFollowerContent)
            if isEnd:
                break

        print('Fetch info end...')

        if getFollowerContent:
            # 存下来，先把list转成文本
            followerText = userId + '\n'
            for text in follower_info:
                followerText += text
            writeFile(userId + '.txt', followerText)
        
    def getFollower(self, datas, follower_info, getFollowerContent=False):
        # 遍历信息并记录
        if datas is not None:
            if self.total <= 0:
                return True
            if getFollowerContent: # 如果不抓取回答内容就不动follower_info，这个函数只做计数作用
                for data in datas:
                    name = data['name']
                    follerNum = data['follower_count']
                    headline = data['headline']
                    follower_info.append(name + '     关注者:' + str(follerNum) + '     个人简介:' + headline)
                    follower_info.append('\n')
            # 请求的向后偏移量
            self.offset += len(datas)
            self.record_num += len(datas)
            # 如果获取的数组size小于limit,循环结束
            if len(datas) < self.limit:
                return True
        return False


    def getAllAnswer(self, questionId, getAnswerContent=False):
        # 存储所有的答案信息
        answer_info = []
        print('Fetch info start...')

        while self.record_num < self.total:
            url = self.getAnswerUrl(questionId)
            def tryFun():
                response = self.session.get(url, headers=self.headers)
                ajson = json.loads(response.content)
                return ajson, response
            ajson, response = catchBan(tryFun)
            writeFile(questionId + '-' + str(self.record_num) + '.json', response.content.decode()) # 把信息存下来
            # 其中的paging实体包含了前一页&下一页的URL，可据此进行循环遍历获取回答的内容
            self.total = ajson['paging']['totals'] # 回答总数
            isEnd = self.getAnswer(ajson['data'], answer_info, getAnswerContent)
            if isEnd:
                break

        print('Fetch info end...')

        if getAnswerContent:
            # 存下来，先把list转成文本
            answerText = questionId + '\n'
            for text in answer_info:
                answerText+=text
            writeFile(questionId + '.txt', answerText)


    def getTitle(self,ajson):
        datas = ajson['data']
        return datas[0]['question']['title']


    def getAnswer(self,datas, answer_info, getAnswerContent=False):
        # 遍历信息并记录
        if datas is not None:
            if self.total <= 0:
                return True
            if getAnswerContent: # 如果不抓取回答内容就不动answer_info，这个函数只做计数作用
                for data in datas:
                    content = self.dr.sub('', data['content'])
                    answer = data['author']['name'] + ' ' + str(data['voteup_count']) + ' 人点赞' + '\n'
                    answer = answer + 'Answer:' + content + '\n'
                    answer_info.append('\n')
                    answer_info.append(answer)
                    answer_info.append('\n')
                    answer_info.append('------------------------------')
                    answer_info.append('\n')
            # 请求的向后偏移量
            self.offset += len(datas)
            self.record_num += len(datas)
            # 如果获取的数组size小于limit,循环结束
            if len(datas) < self.limit:
                return True
        return False
