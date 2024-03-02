# 💡Chat2table，简易表格分析助手

# 一 前言
之前用智谱AI的Chatglm3-6b模型写过一个简单的论文阅读助手，可用来辅助论文阅读等。而像表格，如Excel、CSV文件等内容的分析，也是不可忽略的需要，因此本文同样使用Chatglm3-6b来搭建一个表格分析助手，用于快速分析表格的内容，提取有效的信息。

Chatglm3采用了全新的对话格式，除最基本的对话外，还支持工具调用和代码执行。简单来说，代码执行属于工具调用的子类，只是提示词不一样，而这两种功能是通过修改微调阶段的提示词来实现的。本文展示的模型作用类似代码执行，但是提示词略不一样，并且只用了最常见的对话提示词模板来完成该功能。



# 二 表格理解
读取表格非常简单，使用pandas库中的*read_csv*或者*read_excel*即可。


## 1 直接读取完整的表格内容
利用*to_json*方法将df转化为一个json字符串
```python
def read_from_csv(filename):
	df = pd.read_csv(filename)
	return df.to_json(force_ascii=False)

s = read_from_csv('/test_short.csv')
print(s)
```

> '{"id":{"0":22501,"1":22502,"2":22503,"3":22504,"4":22505,"5":22506,"6":22507,"7":22508},"age":{"0":35,"1":26,"2":44,"3":36,"4":41,"5":24,"6":25,"7":33},"nr_employed":{"0":5205,"1":4925,"2":4947,"3":5203,"4":4992,"5":4993,"6":5155,"7":5034}}'


接着把上述表格内容的字符串放进提示词中
```
prompt = f"已知信息:{s}\n\n请回答问题:age大于35的数量有多少？\n\n"
```

用了上述的提示词生成的python代码如下：
```python
data = {
    "id": {"0": 22501, "1": 22502, "2": 22503, "3": 22504, "4": 22505, "5": 22506, "6": 22507, "7": 22508},
    "age": {"0": 35, "1": 26, "2": 44, "3": 36, "4": 41, "5": 24, "6": 25, "7": 33},
    "nr_employed": {"0": 5205, "1": 4925, "2": 4947, "3": 5203, "4": 4992, "5": 4993, "6": 5155, "7": 5034}
}

# Calculate the number of individuals with age greater than 35
age_greater_than_35 = sum(1 for age in data["age"].values() if age > 35)
age_greater_than_35
```

可以看出，生成的python代码含有原表格的所有内容。



## 2 只读取表格路径和基础信息
```python
import pandas as pd
csv_filename = '/test_short.csv'
query= 'age最大值是多少？'
prompt = f"已知csv文件:{csv_filename}\n\n文件Schema:{pd.read_csv(csv_filename).columns}\n\n问题:{query}\n\n请生成Python代码解决这个问题，将结果赋值给变量result\n\ndPython代码:\n\n"
```

生成的代码：
```python
import pandas as pd

# 读取csv文件
data = pd.read_csv('/test_short.csv')
# 找到age列的最大值
result = data['age'].max()
print(result)
```

可以看出，生成的python代码只有当真正执行的时候才会从文件路径中读取表格内容。



这两种方法的优缺点总结如下：

1.读取完整的表格内容：简单，但是受模型长度限制不能读取太大的表格

2.只读取表格路径和基础信息：需要一个目录用于保存文件，需要给出列的信息，模型根据这些信息生成代码，可以支持非常大的表格

# 三 运行代码字符串
在python脚本中动态执行python代码，可以用*eval*或者*exec*函数。一般来说，*eval*函数只能计算一个表达式的值，而*exec*可以执行复杂的代码，一般是多行的python字符串。
```bash
exec函数定义如下：
exec(object[, globals[, locals]])

参数说明：
object：必选参数，表示需要被指定的Python代码
globals：可选参数，全局变量，同eval函数
locals：可选参数，局部变量，一般指的是代码中用到的变量，同eval函数

返回值：
exec函数的返回值永远为None.
```
除了exec和eval，还可以利用ipython进行代码执行，即用jupyter-notebook的内核来执行代码，这里不赘述。

# 四 核心模块
如前所述，利用文件路径和信息构建合适的提示词：
```python
import pandas as pd
csv_filename = '/test_short.csv'
query= 'age最大值是多少？'
prompt = f"已知csv文件:{csv_filename}\n\n文件Schema:{pd.read_csv(csv_filename).columns}\n\n问题:{query}\n\n请生成Python代码解决这个问题，将结果赋值给变量result\n\ndPython代码:\n\n"
response, history = model.chat(tokenizer, prompt, history=[])
print(response)
```
模型的回答如下：
```python
首先，我们需要导入pandas库，然后读取csv文件。接下来，我们可以使用pandas的`max()`函数来找到age列的最大值，并将结果赋值给变量result。以下是完整的代码：

import pandas as pd
# 读取csv文件
data = pd.read_csv('/test_short.csv')
# 找到age列的最大值
result = data['age'].max()
print(result)

这段代码将输出age列的最大值。
```

接下来用正则提取出模型回答中的python代码部分：
```python
import re
pat = re.compile(r'```python\n([\s\S]+)\n```')
code_string = pat.findall(response)[0]
print(code_string)
```

提取出来的python代码字符串如下：

> "import pandas as pd\n\n# 读取csv文件\ndata = pd.read_csv('/test_short.csv')\n\n# 找到age列的最大值\nresult = data['age'].max()\n\nprint(result)"


利用exec执行代码，并且把结果赋给大模型。注意这时候需要设置参数`role='observation'`：

```python
loc = {}
exec(code_string, None, loc)
response, history = model.chat(tokenizer, f"result:{loc['result']}", history=history, role='observation')
print(response)
```
> 根据提供的CSV文件，age列的最大值是44。


# 五 效果展示
Gradio库有dataframe组件，可以用来显示上传表格的内容，实现预览功能。此外，上传的文档会存放在一个临时的路径下，当会话断开后则删除，不会保存到本地中，不占用本地存储。

表格分析助手搭建效果如图：




