# -*- coding: utf-8 -*-
import re
from collections import OrderedDict
from copy import deepcopy
from itertools import islice

MAX_NUMBER = 20

NUMBER_DELIMITER_SCHEMA_ORDERED_DICT = OrderedDict([
    ('type_(一)', '(%s)'),
    ('type_（一）', '（%s）'),
    ('type_1、', '%s、'),
    ('type_1.', '%s.'),
    ('type_1．', '%s．'),
    ('type_(1)', '(%s)'),
    ('type_1)', '%s)'),
    ('type_①', '%s'),
])


def cn_number_generator():
    cn_numbers = ['零',
                  '一', '二', '三', '四', '五',
                  '六', '七', '八', '九', '十',
                  '一十一', '一十二', '一十三', '一十四', '一十五',
                  '一十六', '一十七', '一十八', '一十九', '二十']
    idx = 0
    while True:
        idx += 1
        if idx >= len(cn_numbers):
            raise StopIteration()
        yield cn_numbers[idx]


def number_delimiter_generator(delimiter_type, delimiter_schema='%s'):
    idx = 0
    if '一' in delimiter_type:
        while True:
            idx += 1
            for cn_number in cn_number_generator():
                yield delimiter_schema % cn_number

    elif '①' in delimiter_type:
        unicode_number = 9312
        while True:
            unicoode_hex_number = '\\u{:x}'.format(unicode_number)
            if unicode_number > 9331:
                raise StopIteration()
            yield delimiter_schema % unicoode_hex_number.encode('ascii').decode('unicode_escape')
            unicode_number += 1
    else:
        while True:
            idx += 1
            yield delimiter_schema % idx


NUMBER_DELIMITERS_ORDERED_DICT = OrderedDict(
    (key, list(islice(number_delimiter_generator(key, schema), MAX_NUMBER)))
    for key, schema in NUMBER_DELIMITER_SCHEMA_ORDERED_DICT.items())


class NumberNode:
    def __init__(self, value, delimiter_type, children=None):
        self.value = value
        self.delimiter_type = delimiter_type
        self.children = children if children else []

    def number_str(self, delimiter_idx):
        bullet_str = NUMBER_DELIMITERS_ORDERED_DICT[self.delimiter_type][
            delimiter_idx] if self.delimiter_type and delimiter_idx is not None else ''
        return bullet_str

    def __str__(self, level=0, delimiter_idx=None, keep_number=True, indent_by='\t'):
        if indent_by is None:
            indent_by = ''
        if not self.value:
            level -= 1
            ret = ''
        else:
            number_str = self.number_str(delimiter_idx) if keep_number else ''
            ret = ''.join((indent_by * level, number_str, str(self.value), '\n'))

        for _delimiter_idx, child in enumerate(self.children):
            ret += child.__str__(level + 1, _delimiter_idx, keep_number, indent_by)
        return ret

    def to_dict(self, delimiter_idx=None, keep_number=True):
        children = []
        result = {
            'value': self.number_str(delimiter_idx) + self.value if keep_number else self.value,
            'children': children
        }

        for idx, child in enumerate(self.children):
            children.append(child.to_dict(idx, keep_number=keep_number))

        return result


class TextNumberedListAnalyser:

    @staticmethod
    def _is_valid_delimiters_in_order(delimiters_candidates, delimiters):
        if delimiters_candidates and delimiters:
            for d_candidate, d in zip(delimiters_candidates, delimiters):
                if d_candidate != d:
                    break
            else:
                return True

        return False

    @classmethod
    def generate_numbered_list_tree(cls, text, exclude_delimiter_types=None):
        if exclude_delimiter_types is None:
            exclude_delimiter_types = []

        current_delimiter_head = exclude_delimiter_types[-1] if exclude_delimiter_types else None

        for delimiter_type in NUMBER_DELIMITERS_ORDERED_DICT.keys():

            if delimiter_type in exclude_delimiter_types:
                continue

            delimiters = NUMBER_DELIMITERS_ORDERED_DICT[delimiter_type]
            delimiters_candidates = re.findall(r'|'.join((re.escape(delimiter) for delimiter in delimiters)), text)

            exclude_delimiter_types.append(delimiter_type)

            if cls._is_valid_delimiters_in_order(delimiters_candidates, delimiters):
                results = re.split(('|'.join(re.escape(delimiter) for delimiter in delimiters)), text)
                node = NumberNode(results[0], current_delimiter_head)
                for line in results[1:]:
                    child_node = cls.generate_numbered_list_tree(line, deepcopy(exclude_delimiter_types))
                    node.children.append(child_node)

                break

        else:
            node = NumberNode(text, current_delimiter_head)

        return node

    @classmethod
    def format_text(cls, text, keep_number=True, indent_by=None):
        root = cls.generate_numbered_list_tree(text)
        return root.__str__(keep_number=keep_number, indent_by=indent_by)


if __name__ == '__main__':
    raw_text = (
        '本基金投资策略:(一)资产配置策略本基金通过定量与定性相结合的方法分析宏观经济和证券市场发展趋势，'
        '评估市场的系统性风险和各类资产的预期收益与风险，据此合理制定和调整各类资产的比例，'
        '在保持总体风险水平相对稳定的基础上，力争投资组合的稳健增值。此外，本基金将持续地进行定期与不定期的资产配置风险监控，'
        '适时地做出相应的调整。(二)股票投资策略本基金通过量化分析与基本面分析相结合的研究方式，以公司经营质量、营业收入、公司盈利、'
        '分析师预期和估值等为主要关注点，以新兴行业中处于合理价位的成长型股票(GrowthatReasonablePrice，GARP)为主要投资标的，'
        '并兼顾受惠于盈利周期加速且估值相对较低的价值型股票。价值增长投资策略兼顾价值投资和成长投资，'
        '主要投资对象为价值相对低估且未来具有较好成长潜力的股票。该策略甄别未来较具成长性且安全边际较高的个股。'
        '投资决策流程(1)量化分析本基金通过自主研发的量化模型体系来初步筛选样本股。在本基金所设定的投资范围和投资限制的基础上，'
        '利用财务信息、价格信息及分析师预期信息等，以公司经营质量、营业收入、公司盈利、分析师预期和估值等数据为因子集群，'
        '通过自主研发的量化模型体系来对上市公司进行评分，筛选出公司经营质量较好、主营业务或利润增速较快、价值相对被低估或成长性较好的个股，'
        '建立基本股票池。在基本股票池的基础上，本基金还会利用大数据，找寻大数据与股价之间的相关关系，'
        '力争进一步提高量化模型的有效性。(2)基本面分析本基金通过严谨的基本面分析来对由量化模型筛选出来股票进行进一步精选。'
        '基金经理及研究部利用投资研究平台，根据其对中国整体经济、行业及上市公司进行的深入研究与分析，对上市公司进行财务诊断、'
        '竞争力分析、盈利能力分析和成长性分析，并运用合适的价值评估手段进行估值，找出最有投资机会的公司，'
        '建立精选股票池。(3)投资组合构建根据量化模型评分及基本面分析的结果，本基金在精选股票池中进行股票选择，'
        '采取评分越高权重越大及自由流通市值加权的方式相结合，构建股票投资组合，以期获取中长期投资收益。'
        '(三)债券投资策略本基金的债券投资将采取较为积极的策略，通过利率预测分析、收益率曲线变动分析、债券信用分析、收益率利差分析等，'
        '力求在保证基金资产总体的安全性、流动性的基础上获取一定的稳定收益。(四)衍生品投资策略本基金可以参与衍生品投资，'
        '主要用于组合风险管理和流动性管理。选择流动性好、交易活跃的金融衍生品，力争运用衍生品的杠杆作用，'
        '降低申购赎回时现金资产对投资组合的影响及投资组合仓位调整的交易成本，以套期保值为目的，达到稳定投资组合资产净值的作用。'
    )
    formatted_text = TextNumberedListAnalyser.format_text(raw_text.strip(), keep_number=True, indent_by='\t')
    print(formatted_text)
