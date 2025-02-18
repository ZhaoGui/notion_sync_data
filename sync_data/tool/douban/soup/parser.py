# -*- coding: utf-8 -*-
# @Author  : Qliangw
# @Time    : 2022/3/1 21:05
# @Function: 使用bs4查找html相关数据
import datetime
import re

from bs4 import BeautifulSoup
from sync_data.tool.douban.data.enum_data import MediaType, MediaInfo
from sync_data.utils import log_detail

# 解析参考 https://zhuanlan.zhihu.com/p/54195299


class ParserHtmlText:
    """
    使用BeautifulSoup解析html
    """
    def __init__(self, html_text):
        self.html = html_text
        self.soup = BeautifulSoup(self.html, 'html.parser')

    def get_url_dict(self, monitoring_day=0):
        """
        解析个人wish/do/collect内容的每个url

        :return: { url_list: [url数组], monitoring_info: [符合日期的个数,是否继续]}
        """
        record_key = 0
        url_list = []
        continue_request = True
        monitoring_info = [0, continue_request]
        url_dict = {}
        try:
            info = self.soup.select('.nbg')
            for url in info:
                url_list.append(url.get('href'))

            if monitoring_day != 0:
                mark_date = self.soup.select('span.date')
                # 处理所有标记时间
                num = 0
                mark_date_dict = {}
                while num < len(mark_date):
                    mark_date_dict[num] = list(mark_date[num].strings)
                    # mark_date_dict[num] = ''.join([i.rstrip()[:-9] for i in mark_date_dict[num] if i.strip() != ''])
                    mark_date_dict[num] = ''.join([i.split("\n", 1)[0] for i in mark_date_dict[num] if i.strip() != ''])
                    num += 1

                # 获取当天时间
                today = datetime.datetime.now()
                today = datetime.datetime.now()
                log_detail.warn(f"【RUN】当前时间为：{today}")

                # 判断 标记时间
                # 符合监控日期内媒体个数计数
                count_num = 0
                for key in mark_date_dict:
                    mark_date_i = datetime.datetime.strptime(mark_date_dict.get(key), '%Y-%m-%d')
                    interval = today - mark_date_i
                    if interval.days <  monitoring_day:
                        log_detail.debug(f'第{count_num}个的{key}数据{mark_date_i}与当天相差{interval}天')
                        count_num += 1
                    else:
                        log_detail.debug(f"第{count_num}个的{key}数据{mark_date_i}超出时间范围，不处理")
                        record_key = int(key)
                        break
                log_detail.debug(f"【RUN】监控日期内，对应的位置{record_key}")
            else:
                # 如果没有监控日期，与媒体个数相同即可
                record_key = len(url_list)
                count_num = len(url_list)

            # 如果该页媒体为15，且监控没有限制或者都在监控日期内，则继续获取下一页内容
            if len(url_list) == 15 and count_num == len(url_list):
                continue_request = True
            else:
                continue_request = False

            monitoring_info[0] = record_key
            monitoring_info[1] = continue_request
            url_dict["url_list"] = url_list
            url_dict["monitoring_info"] = monitoring_info
            return url_dict

        except Exception as err:
            log_detail.warn(f"【RUN】解析失败：{err}")
            return url_dict

    def get_url_list(self):
        """
        解析个人wish/do/collect内容的每个url

        :return: url数组
        """
        url_list = []
        try:
            info = self.soup.select('.nbg')
            for url in info:
                url_list.append(url.get('href'))
            return url_list
        except Exception as err:
            log_detail.warn(f"【RUN】解析失败：{err}")
            return []

    def get_parser_dict(self, media_type):
        """
        解析网页，抓取数据

        :param media_type: 媒体类型，使用enum_data的枚举类
        :return: 数据字典，提取key在enum_data的MediaInfo中
        """
        try:
            self.__parser(media_type=media_type)
            return self.dict
        except Exception as err:
            log_detail.warn(f"【RUN】解析失败：{err}")
            return []

    def __parser(self, media_type):
        # parser_dict = {}
        # soup = BeautifulSoup(self.html, 'lxml')
        # self.soup = BeautifulSoup(self.html, 'html.parser')
        if media_type == MediaType.BOOK.value:
            self.dict = self.__get_book_dict()
        elif media_type == MediaType.MUSIC.value:
            self.dict = self.__get_music_dict()
        elif media_type == MediaType.MOVIE.value:
            # log_detail.warn("【RUN】暂不支持电影、电视剧的导入！")
            self.dict = self.__get_movie_dict()
        else:
            pass

    def __get_book_dict(self):
        log_detail.debug("【RUN】解析书籍信息")
        # 标签名不加任何修饰，类名前加点，id名前加#
        info = self.soup.select('#info')
        infos = list(info[0].strings)
        infos = [i.strip() for i in infos if i.strip() != '']
        book_dict = {}

        # 书名
        title = self.soup.select('#wrapper > h1 > span')[0].contents[0]

        # 作者
        if '作者:' in infos:
            book_author = infos[infos.index('作者:') + 1]
        elif self.soup.select('#info > span > a'):
            book_author = self.soup.select('#info > span > a')[0].contents[0]
        else:
            book_author = ""
        book_author = ''.join(map(str.strip, book_author.split('\n')))

        # 出版社 副标题 出版年 页数 定价 ISBN
        book_publisher = infos[infos.index('出版社:') + 1] if '出版社:' in infos else ""
        book_publisher = book_publisher.replace(',', '')
        book_subhead = infos[infos.index('副标题:') + 1] if '副标题:' in infos else ""
        book_pub_date = infos[infos.index('出版年:') + 1] if '出版年:' in infos else ""
        book_pages = infos[infos.index('页数:') + 1] if '页数:' in infos else ""
        book_price = infos[infos.index('定价:') + 1] if '定价:' in infos else ""
        # https://isbnsearch.org/isbn/{ISBN}
        book_isbn = infos[infos.index('ISBN:') + 1] if 'ISBN:' in infos else ""

        # 评分 评价数 图片网址
        rating_list = get_media_rating_list(self.soup)
        book_img = self.soup.select("#mainpic > a > img")[0].attrs['src']

        # 价格
        book_price_list = [float(s) for s in re.findall(r'-?\d+\.?\d*', book_price)]
        if len(book_price_list):
            book_price = book_price_list[0]
        else:
            book_price = 0

        # 简介
        related_info = self.soup.select("div.intro")
        related_infos = get_media_related_infos(related_info)

        book_dict[MediaInfo.TITLE.value] = title
        book_dict[MediaInfo.AUTHOR.value] = book_author
        book_dict[MediaInfo.PUBLISHER.value] = book_publisher
        book_dict[MediaInfo.SUBHEAD.value] = book_subhead
        book_dict[MediaInfo.PUB_DATE.value] = book_pub_date
        book_dict[MediaInfo.PAGES.value] = book_pages
        book_dict[MediaInfo.PRICE.value] = book_price
        book_dict[MediaInfo.ISBN.value] = book_isbn
        book_dict[MediaInfo.RATING_F.value] = float(rating_list[0])
        book_dict[MediaInfo.ASSESS.value] = int(rating_list[1])
        book_dict[MediaInfo.IMG.value] = book_img
        book_dict[MediaInfo.RELATED.value] = related_infos
        return book_dict

    def __get_music_dict(self):
        log_detail.debug("【RUN】解析音乐信息")
        info = self.soup.select('#info')
        infos = list(info[0].strings)
        infos = [i.strip() for i in infos if i.strip() != '']
        music_dict = {}

        # 歌曲名称
        title = self.soup.select('#wrapper > h1 > span')[0].contents[0]

        # 表演者
        if '表演者:' in infos:
            music_performer = infos[infos.index('表演者:') + 1]
        elif self.soup.select('#info > span > a'):
            music_performer = self.soup.select('#info > span > a')[0].contents[0]
        else:
            music_performer = ''
        music_performer = ''.join(map(str.strip, music_performer.split('\n')))

        # 流派 专辑类型 介质 发行时间 出版者 条形码
        music_genre = infos[infos.index('流派:') + 1] if '流派:' in infos else ""
        album_type = infos[infos.index('专辑类型:') + 1] if '专辑类型:' in infos else ""
        music_medium = infos[infos.index('介质:') + 1] if '介质:' in infos else ""
        music_release_date = infos[infos.index('发行时间:') + 1] if '发行时间:' in infos else ""
        music_isrc = infos[infos.index('条形码:') + 1] if '条形码:' in infos else ""

        # 评分 评价数 图片url
        # rating = self.soup.select("#interest_sectl > div > div.rating_self.clearfix > strong")
        # music_rating = rating[0].contents[0] if rating else 0
        rating_list = get_media_rating_list(self.soup)


        # music_assesses = self.soup.select(
        #     "#rating_right > div.rating_sum > a")
        # # print(music_assesses)
        # music_assess = music_assesses[0].contents[0] if music_assesses else ""
        music_img = self.soup.select("#mainpic > span > a > img")[0].attrs['src']

        music_dict[MediaInfo.TITLE.value] = title
        music_dict[MediaInfo.PERFORMER.value] = music_performer
        music_dict[MediaInfo.ALBUM_TYPE.value] = album_type
        music_dict[MediaInfo.GENRE.value] = music_genre
        music_dict[MediaInfo.MEDIUM.value] = music_medium
        music_dict[MediaInfo.RELEASE_DATE.value] = music_release_date
        music_dict[MediaInfo.ISRC.value] = music_isrc
        music_dict[MediaInfo.RATING_F.value] = float(rating_list[0])
        music_dict[MediaInfo.ASSESS.value] = int(rating_list[1])
        music_dict[MediaInfo.IMG.value] = music_img
        return music_dict


    def __get_movie_dict(self):
        log_detail.debug("【RUN】解析影视信息")
        # 标签名不加任何修饰，类名前加点，id名前加#
        info = self.soup.select('#info')
        infos = list(info[0].strings)
        infos = [i.strip() for i in infos if i.strip() != '']
        movie_dict = {}
        # 影视名称
        title = self.soup.select('#wrapper > div > h1')
        titles = list(title[0].strings)
        titles = [i.strip() for i in titles if i.strip() != '']
        movie_title = ''.join(titles)

        # 导演
        if '导演' in infos:
            movie_director = multiple_infos_parser(infos, '导演', 2)
        else:
            movie_director = ""

        # 编剧 主演 类型
        screenwriter = multiple_infos_parser(infos, "编剧", 2)
        starring = multiple_infos_parser(infos, "主演", 2)
        movie_type = multiple_infos_parser(infos, "类型:" , 1)

        # 国家或地区 语言
        c_or_r = get_simple_info_list(infos, "制片国家/地区:")
        language_list = get_simple_info_list(infos, "语言:")

        # 分类 电影和电视剧 以及 动画片（电影）和动漫（剧集）
        if '上映时间:' in infos or '上映日期:' in infos:
            if '动画' in movie_type:
                movie_categories = "动画片"
            else:
                movie_categories = '电影'
        elif "首播:" in infos or "首播时间:" in infos:
            if '动画' in movie_type:
                movie_categories = "动漫"
            else:
                movie_categories = "电视剧"
        else:
            movie_categories = "未知"

        imdb = infos[infos.index('IMDb:') + 1] if 'IMDb' in infos else ""

        # 评分 评价数
        rating_list = get_media_rating_list(self.soup)

        # 图片网址
        movie_img = self.soup.select("#mainpic > a > img")[0].attrs['src']

        # 简介
        related_info = self.soup.select("#content > div > div.article > div > div.indent > span")
        related_infos = get_media_related_infos(related_info)

        # print(rating_infos)

        movie_dict[MediaInfo.TITLE.value] = movie_title
        movie_dict[MediaInfo.DIRECTOR.value] = movie_director
        movie_dict[MediaInfo.SCREENWRITER.value] = screenwriter
        movie_dict[MediaInfo.STARRING.value] = starring
        movie_dict[MediaInfo.MOVIE_TYPE.value] = movie_type
        movie_dict[MediaInfo.C_OR_R.value] = c_or_r
        movie_dict[MediaInfo.LANGUAGE.value] = language_list
        movie_dict[MediaInfo.CATEGORIES.value] = movie_categories
        movie_dict[MediaInfo.IMDB.value] = imdb
        movie_dict[MediaInfo.RATING_F.value] = float(rating_list[0])
        movie_dict[MediaInfo.ASSESS.value] = int(rating_list[1])
        movie_dict[MediaInfo.IMG.value] = movie_img
        movie_dict[MediaInfo.RELATED.value] = related_infos
        return movie_dict

    def get_music(self):
        infos = self.__get_music_dict()
        # log_detail.info(f"{infos}")
        return infos

def get_simple_info_list(str_dict, str_key):
    str_list = []
    try:
        if str_key in str_dict:
            data_list_tmp = str_dict[str_dict.index(str_key) + 1]
            data_list_tmp = data_list_tmp.split('/')

            for i in data_list_tmp:
                str_list.append(i.strip(' '))
        else:
            log_detail.warn(f"【RUN】未解析到<{str_key}>信息")
        return str_list
    except Exception as err:
        log_detail.error(f"【RUN】未解析到<{str_key}>信息:{err}")
        return str_list

def multiple_infos_parser(str_dict, str_key, next_number):
    str_list = []
    try:
        if str_key in str_dict:

            first_index = str_dict.index(str_key) + next_number
            str_list.append(str_dict[first_index])
            next_index = first_index
            while True:
                if str_dict[next_index + 1] == '/':
                    next_index += 2
                    str_list.append(str_dict[next_index])
                else:
                    break
        else:
            log_detail.warn(f"【RUN】未解析到{str_key}数据，返回空值")
        return str_list
    except Exception as err:
        log_detail.error(f"【RUN】未解析到{str_key}数据：{err}")
        return  str_list

def get_media_rating_list(soup):
    rating_list = ['0', '0']
    try:
        rating_info = soup.select("#interest_sectl > div > div.rating_self.clearfix")
        rating_infos = list(rating_info[0].strings)
        rating_infos = [i.strip() for i in rating_infos if i.strip() != '']
        if len(rating_infos) > 2:
            rating_list = rating_infos
            # rating_list[1] = rating_infos[1]
        else:
            rating_list[0] = 0.0
            rating_list[1] = 0
        return rating_list
    except Exception as err:
        log_detail.warn(f"【RUN】未解析到评价数据{err}")
        return rating_list

def get_media_related_infos(info):
    try:
        if info:
            related_infos = list(info[0].strings)
            related_infos = [i.strip() for i in related_infos if i.strip() != '']
            related_infos = "\n".join(related_infos)
            return related_infos
        else:
            return "暂无。"
    except Exception as err:
        log_detail.warn(f"【RUN】未解析到简介{err}")
        return "暂无。。。"