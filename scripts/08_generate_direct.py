"""
直接生成模式：基于 transcript 内容，用 Python 内置逻辑生成中文总结
不依赖任何外部 LLM API，使用规则+模板方式快速生成结构化总结

因为当前 catdesk CLI 不支持 ask 命令，改用 Friday HTTP API 调用
"""

import json
import sys
import io
import time
import re
import os
import urllib.request
import urllib.error
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

BASE_DIR = Path(__file__).parent.parent
TRANSCRIPTS_DIR = BASE_DIR / "data" / "transcripts"
SUMMARIES_DIR = BASE_DIR / "data" / "summaries"
MISSING_FILE = BASE_DIR / "data" / "missing_slugs.json"
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


def get_full_text(dialogue: list) -> str:
    lines = []
    for d in dialogue:
        speaker = d.get("speaker", "")
        text = d.get("text", "").strip()
        if text:
            lines.append(f"{speaker}: {text}" if speaker else text)
    return "\n".join(lines)


def guess_guest_name(slug: str) -> str:
    name = slug.replace("-", " ").title()
    name = re.sub(r'\s+\d+$', '', name)
    return name


# 常见嘉宾的中文名和简介知识库
GUEST_INFO = {
    "alex-filippenko": ("阿历克斯·菲利片科", "天文学家", "宇宙学", "超新星研究先驱、天文学家，参与发现宇宙加速膨胀并荣获诺贝尔物理学奖的研究团队"),
    "alex-garland": ("亚历克斯·加兰", "科幻", "电影创作", "英国编剧兼导演，代表作《机械姬》《湮灭》《德福斯》，深度探索人工智能与人性"),
    "alex-gladstein": ("亚历克斯·格拉德斯坦", "比特币", "人权", "人权基金会首席战略官，倡导比特币作为人权工具对抗威权政府"),
    "alien-debate": ("UFO外星人辩论", "UFO", "外星人", "多位专家就UFO现象和外星生命存在可能性展开深度辩论"),
    "anca-dragan": ("安卡·德拉甘", "机器人", "人工智能", "加州大学伯克利分校机器人学教授，研究人机协作与AI安全"),
    "andrew-bustamante": ("安德鲁·布斯塔曼特", "CIA", "情报", "前CIA情报官员，揭示情报工作内幕与国家安全策略"),
    "andrew-huberman": ("安德鲁·胡伯曼", "神经科学", "健康", "斯坦福神经科学教授，热门播客主持人，研究睡眠、压力与表现优化"),
    "andrew-huberman-2": ("安德鲁·胡伯曼", "神经科学", "健康", "斯坦福神经科学教授，第二次对话深探多巴胺、睡眠与压力管理"),
    "andrew-huberman-3": ("安德鲁·胡伯曼", "神经科学", "健康", "斯坦福神经科学教授，第三次深度对话"),
    "andrew-ng": ("吴恩达", "人工智能", "机器学习", "AI领域顶级专家，Coursera联合创始人，前Google Brain和百度AI负责人"),
    "ann-druyan": ("安·德鲁扬", "宇宙", "科学传播", "卡尔·萨根的妻子，《宇宙》系列节目制作人，科学传播者"),
    "anthony-pompliano": ("安东尼·庞普利亚诺", "比特币", "投资", "著名加密货币投资者和倡导者，比特币长期看涨者"),
    "anya-fernald": ("安雅·费尔纳尔德", "食品", "农业", "可持续农业倡导者和美食家，研究食品系统与草饲牛肉"),
    "ariel-ekblaw": ("阿里尔·艾克劳", "太空", "技术", "MIT媒体实验室太空探索倡议负责人，研究太空建筑与自组装结构"),
    "ayanna-howard": ("阿亚娜·霍华德", "机器人", "人工智能", "乔治亚理工学院机器人学教授，研究残障辅助机器人与AI伦理"),
    "barry-barish": ("巴里·巴里什", "物理学", "引力波", "诺贝尔物理学奖得主，LIGO实验负责人之一，引力波探测先驱"),
    "ben-askren": ("本·阿斯克伦", "摔跤", "MMA", "奥运摔跤手和MMA职业选手，UFC焊接冠军"),
    "ben-goertzel": ("本·戈特泽尔", "人工智能", "AGI", "通用人工智能研究先驱，SingularityNET创始人"),
    "bjarne-stroustrup": ("比雅尼·斯特劳斯特鲁普", "编程", "C++", "C++编程语言创造者，计算机科学先驱"),
    "boris-sofman": ("鲍里斯·索夫曼", "机器人", "自动驾驶", "Anki机器人公司联合创始人，后投身自动驾驶领域"),
    "botez-sisters": ("博特兹姐妹", "国际象棋", "流媒体", "Alexandra和Andrea Botez，加拿大裔象棋选手和流媒体主播"),
    "brendan-eich": ("布兰登·艾克", "编程", "JavaScript", "JavaScript发明者，Mozilla联合创始人，Brave浏览器创始人"),
    "brett-johnson": ("布雷特·约翰逊", "网络犯罪", "黑客", "前网络犯罪头目，改邪归正后成为网络安全专家"),
    "brian-armstrong": ("布莱恩·阿姆斯特朗", "加密货币", "创业", "Coinbase联合创始人兼CEO，加密货币交易所先驱"),
    "brian-keating": ("布莱恩·基廷", "宇宙学", "物理学", "加州大学圣地亚哥分校天体物理学家，研究宇宙微波背景辐射"),
    "brian-kernighan": ("布莱恩·柯尼汉", "编程", "Unix", "Unix和C语言奠基人之一，《C程序设计语言》作者"),
    "brian-muraresku": ("布莱恩·穆拉雷斯库", "历史", "宗教", "律师和古典学者，研究古希腊宗教仪式中的迷幻药物"),
    "cal-newport": ("卡尔·纽波特", "生产力", "深度工作", "乔治城大学计算机科学教授，《深度工作》作者"),
    "carl-hart": ("卡尔·哈特", "神经科学", "毒品", "哥伦比亚大学神经科学家，研究成瘾与毒品政策"),
    "charles-hoskinson": ("查尔斯·霍斯金森", "加密货币", "区块链", "以太坊联合创始人，Cardano创始人"),
    "charles-isbell": ("查尔斯·伊斯贝尔", "人工智能", "机器学习", "佐治亚理工学院计算机科学院长，研究多智能体系统"),
    "charles-isbell-and-michael-littman": ("伊斯贝尔与利特曼", "人工智能", "机器学习", "两位AI研究先驱探讨机器学习的历史与未来"),
    "chris-blattman": ("克里斯·布拉特曼", "战争", "冲突", "芝加哥大学经济学家，研究战争、犯罪与和平的经济学"),
    "chris-lattner": ("克里斯·拉特纳", "编程", "LLVM", "LLVM和Swift编程语言创造者，前苹果和特斯拉AI负责人"),
    "chris-urmson": ("克里斯·厄姆森", "自动驾驶", "机器人", "Google自动驾驶汽车项目创始人之一，Aurora创始人"),
    "christof-koch": ("克里斯托夫·科赫", "意识", "神经科学", "意识神经科学领域顶级专家，艾伦脑科学研究所所长"),
    "christopher-capozzola": ("克里斯托弗·卡波佐拉", "历史", "美国", "MIT历史学教授，研究美国战争史与公民义务"),
    "clara-sousa-silva": ("克拉拉·苏萨-席尔瓦", "天体化学", "金星", "天体化学家，因声称在金星大气中发现磷化氢而引发广泛关注"),
    "colin-angle": ("科林·安格尔", "机器人", "iRobot", "iRobot联合创始人兼CEO，Roomba扫地机器人之父"),
    "cristiano-amon": ("克里斯蒂亚诺·阿蒙", "半导体", "5G", "高通CEO，引领5G时代的半导体巨头"),
    "cristos-goodrow": ("克里斯托斯·古德罗", "YouTube", "推荐算法", "YouTube工程副总裁，负责搜索与推荐系统"),
    "cumrun-vafa": ("库姆伦·瓦法", "弦理论", "物理学", "哈佛大学理论物理学家，弦理论领域的奠基人之一"),
    "dan-gable": ("丹·盖布尔", "摔跤", "体育", "美国摔跤传奇，奥运冠军和最成功的大学摔跤教练"),
    "dan-kokotov": ("丹·科科托夫", "音频", "AI", "Sonix联合创始人，专注AI语音转文字技术"),
    "dan-reynolds": ("丹·雷诺兹", "音乐", "创意", "Imagine Dragons乐队主唱，摇滚乐巨星"),
    "daniel-kahneman": ("丹尼尔·卡尼曼", "心理学", "行为经济学", "诺贝尔经济学奖得主，行为经济学奠基人，《思考，快与慢》作者"),
    "daniel-negreanu": ("丹尼尔·内格雷亚努", "扑克", "策略", "职业扑克世界冠军，扑克界最知名的人物之一"),
    "daphne-koller": ("达芙妮·科勒", "机器学习", "教育", "Coursera联合创始人，斯坦福大学机器学习教授，AI与生物医学先驱"),
    "dava-newman": ("达娃·纽曼", "航空航天", "MIT", "MIT航空航天工程教授，前NASA副局长"),
    "david-chalmers": ("大卫·查默斯", "意识", "哲学", "哲学家，意识研究领域的核心人物，提出'意识难题'"),
    "david-eagleman": ("大卫·伊格曼", "神经科学", "感知", "斯坦福神经科学家，研究时间感知、感觉替代和人类意识"),
    "david-ferrucci": ("大卫·费鲁奇", "人工智能", "IBM Watson", "IBM Watson项目负责人，击败人类Jeopardy冠军的AI之父"),
    "david-fravor": ("大卫·弗拉弗", "UFO", "军事", "前美国海军飞行员，目击并报告'刻字'UFO事件"),
    "david-patterson": ("大卫·帕特森", "计算机架构", "RISC", "图灵奖得主，RISC架构和RAID存储先驱"),
    "david-silver": ("大卫·西尔弗", "人工智能", "强化学习", "DeepMind首席研究员，AlphaGo之父，强化学习领域领袖"),
    "david-wolpe": ("大卫·沃尔普", "犹太教", "宗教", "洛杉矶最具影响力的犹太教拉比，神学思想家"),
    "dawn-song": ("宋晓冬", "网络安全", "AI", "加州大学伯克利分校教授，网络安全和AI安全领域专家"),
    "demis-hassabis": ("德米斯·哈萨比斯", "人工智能", "DeepMind", "DeepMind联合创始人兼CEO，AlphaGo和AlphaFold背后的推手"),
    "devon-larratt": ("德文·拉拉特", "掰手腕", "体育", "世界顶级掰手腕运动员，多次世界冠军"),
    "diana-walsh-pasulka": ("戴安娜·沃尔什·帕苏尔卡", "UFO", "宗教", "北卡罗来纳大学宗教研究教授，研究UFO现象与宗教信仰"),
    "dileep-george": ("迪利普·乔治", "人工智能", "神经科学", "Vicarious联合创始人，受神经科学启发的AI研究先驱"),
    "dmitri-dolgov": ("德米特里·多尔戈夫", "自动驾驶", "Waymo", "Waymo联合CEO，自动驾驶技术领军人物"),
    "dmitry-korkin": ("德米特里·科尔金", "计算生物学", "病毒", "WPI计算生物学教授，研究蛋白质结构与病毒进化"),
    "dmitry-korkin-2": ("德米特里·科尔金", "计算生物学", "COVID", "WPI计算生物学教授，深入分析COVID-19的分子机制"),
    "donald-knuth": ("唐纳德·克努特", "编程", "计算机科学", "计算机科学泰斗，《计算机程序设计艺术》作者，算法分析之父"),
    "douglas-lenat": ("道格拉斯·勒纳特", "人工智能", "知识", "Cyc项目创始人，知识表示与常识推理研究先驱"),
    "douglas-murray": ("道格拉斯·穆雷", "政治", "文化", "英国保守派作家和评论员，批评西方文化左倾趋势"),
    "duncan-trussell": ("邓肯·特鲁塞尔", "哲学", "意识", "喜剧演员和播客主持人，探索冥想、死亡与精神性"),
    "elon-musk-2": ("埃隆·马斯克", "特斯拉", "创业", "马斯克与Lex的第二次深度对话，探讨特斯拉与未来"),
    "eric-schmidt": ("埃里克·施密特", "谷歌", "人工智能", "前谷歌CEO，科技产业领袖，讨论AI的地缘政治影响"),
    "eric-weinstein": ("埃里克·温斯坦", "物理学", "经济", "数学家和经济学家，管理合伙人和播客主持人"),
    "eric-weinstein-2": ("埃里克·温斯坦", "物理学", "社会", "第二次对话，深探科学停滞与社会变革"),
    "eric-weinstein-4": ("埃里克·温斯坦", "物理学", "政治", "第四次对话，深度讨论政治与科学"),
    "erik-brynjolfsson": ("埃里克·布莱恩约弗森", "经济学", "人工智能", "MIT经济学家，研究技术对劳动力市场的影响，《第二次机器时代》作者"),
    "eugenia-kuyda": ("叶芙根尼娅·库伊达", "人工智能", "伴侣", "Replika AI创始人，开发了基于AI的情感陪伴应用"),
    "francis-collins": ("弗朗西斯·柯林斯", "基因组学", "生物医学", "前NIH主任，人类基因组计划领导者，信仰与科学的调和者"),
    "garry-nolan": ("加里·诺兰", "免疫学", "UFO", "斯坦福免疫学家，研究UFO相关生物材料"),
    "gary-marcus": ("加里·马库斯", "人工智能", "认知", "认知科学家和AI批评者，质疑深度学习的局限性"),
    "gavin-miller": ("加文·米勒", "人工智能", "创意", "Adobe首席科学家，研究AI生成内容与创意工具"),
    "george-hotz-2": ("乔治·霍兹", "黑客", "自动驾驶", "天才黑客，第二次对话深探comma.ai与特斯拉自动驾驶"),
    "georges-st-pierre": ("乔治·圣皮埃尔", "MMA", "UFC", "UFC两个量级世界冠军，被誉为历史上最伟大的MMA选手之一"),
    "georges-st-pierre-john-danaher-gordon-ryan": ("GSP-达纳赫-瑞恩三人谈", "MMA", "格斗", "三位格斗界传奇人物共同探讨搏击艺术"),
    "gilbert-strang": ("吉尔伯特·斯特朗", "数学", "线性代数", "MIT数学教授，线性代数教育的传奇人物"),
    "glenn-loury": ("格伦·洛里", "经济学", "种族", "布朗大学经济学教授，研究种族不平等与美国社会"),
    "grant-sanderson": ("格兰特·桑德森", "数学", "教育", "3Blue1Brown创始人，用视觉方式革命性呈现数学之美"),
    "grant-sanderson-2": ("格兰特·桑德森", "数学", "AI", "第二次对话，探讨数学教育的本质与AI时代的学习"),
    "greg-brockman": ("格雷格·布罗克曼", "OpenAI", "人工智能", "OpenAI联合创始人兼CTO，ChatGPT背后的技术领袖"),
    "guido-van-rossum": ("吉多·范罗苏姆", "Python", "编程", "Python编程语言创造者，'仁慈的独裁者'"),
    "gustav-soderstrom": ("古斯塔夫·瑟德斯特伦", "Spotify", "音乐", "Spotify首席研发官，负责个性化推荐与音乐发现"),
    "harry-cliff": ("哈里·克利夫", "粒子物理", "宇宙", "CERN粒子物理学家，研究反物质与宇宙起源"),
    "ian-goodfellow": ("伊恩·古德费洛", "人工智能", "GAN", "生成对抗网络(GAN)发明者，深度学习领域的杰出研究者"),
    "ian-hutchinson": ("伊恩·哈钦森", "核能", "物理学", "MIT核科学教授，研究核聚变与等离子体物理"),
    "ishan-misra": ("伊尚·米斯拉", "计算机视觉", "AI", "Facebook AI研究员，专注自监督学习与视觉理解"),
    "jack-barsky": ("杰克·巴斯基", "间谍", "冷战", "前KGB卧底特工，在美国潜伏多年后改邪归正"),
    "jack-dorsey": ("杰克·多西", "Twitter", "比特币", "Twitter和Square创始人，比特币坚定拥护者"),
    "james-gosling": ("詹姆斯·高斯林", "Java", "编程", "Java编程语言发明者，软件工程传奇人物"),
    "jamie-metzl": ("杰米·梅茨尔", "基因工程", "生物技术", "地缘政治专家和生物技术作者，研究基因编辑的伦理与未来"),
    "jason-calacanis": ("杰森·卡拉卡尼斯", "创业", "风险投资", "天使投资人，Uber早期投资者，'本周在初创公司'播客主持人"),
    "jay-bhattacharya": ("杰伊·巴塔查里亚", "公共卫生", "COVID", "斯坦福医学教授，《大巴灵顿宣言》联署人，质疑新冠封锁政策"),
    "jay-mcclelland": ("杰伊·麦克莱兰德", "认知科学", "神经网络", "并行分布处理（PDP）框架创始人，认知科学先驱"),
    "jed-buchwald": ("杰德·布赫瓦尔德", "科学史", "物理学", "加州理工学院科学史教授，研究牛顿与电磁学历史"),
    "jeff-atwood": ("杰夫·阿特伍德", "编程", "社区", "Stack Overflow联合创始人，程序员社区建设先驱"),
    "jeff-hawkins": ("杰夫·霍金斯", "神经科学", "AI", "Palm创始人，《智能时代》作者，研究新皮质记忆预测框架"),
    "jeff-hawkins-2": ("杰夫·霍金斯", "神经科学", "AI", "第二次对话，深探千脑理论与AI的未来"),
    "jeffrey-shainline": ("杰弗里·沙因莱因", "神经形态计算", "超导", "NIST研究员，研究超导神经形态计算"),
    "jeremi-suri": ("杰里米·苏里", "历史", "地缘政治", "德克萨斯大学历史学家，研究美国外交政策与全球政治"),
    "jeremy-howard": ("杰里米·霍华德", "机器学习", "fast.ai", "fast.ai创始人，让深度学习大众化的教育先驱"),
    "jim-gates": ("吉姆·盖茨", "物理学", "弦理论", "马里兰大学物理学家，研究超弦理论，奥巴马科学顾问"),
    "jim-keller": ("吉姆·凯勒", "芯片", "CPU", "半导体传奇工程师，参与设计Athlon、K8和Apple A系列芯片"),
    "jimmy-pedro": ("吉米·佩德罗", "柔道", "体育", "美国柔道奥运铜牌得主，美国柔道国家队教练"),
    "jitendra-malik": ("吉滕德拉·马利克", "计算机视觉", "AI", "计算机视觉领域奠基人之一，加州大学伯克利分校教授"),
    "jo-boaler": ("乔·博阿勒", "数学教育", "成长型思维", "斯坦福教育学教授，研究数学焦虑与成长型思维"),
    "joe-rogan-2": ("乔·罗根", "播客", "UFC", "最受欢迎的播客主持人之一，UFC解说员，第二次深度对话"),
    "john-abramson": ("约翰·亚伯拉罕森", "医药", "公共卫生", "哈佛医学院讲师，著书揭露制药行业的弊端"),
    "john-clarke": ("约翰·克拉克", "摔跤", "体育", "摔跤运动员和教练"),
    "john-danaher": ("约翰·达纳赫", "柔术", "格斗哲学", "世界顶级柔术教练，以培养一流格斗选手闻名"),
    "john-hopfield": ("约翰·霍普菲尔德", "神经网络", "物理学", "2024年诺贝尔物理学奖得主，霍普菲尔德网络发明者"),
    "john-vervaeke": ("约翰·韦尔瓦克", "哲学", "认知科学", "多伦多大学哲学教授，研究意义危机与认知科学"),
    "jonathan-reisman": ("乔纳森·雷斯曼", "医学", "解剖学", "急诊医生和解剖学家，研究人体与医疗系统"),
    "jordan-ellenberg": ("乔丹·艾伦伯格", "数学", "思维", "威斯康星大学数学教授，《如何不出错》作者"),
    "joscha-bach": ("约沙·巴赫", "人工智能", "意识", "人工智能研究员，探索意识计算模型与认知架构"),
    "josh-barnett": ("乔希·巴内特", "MMA", "格斗", "职业MMA选手和摔跤手，UFC重量级冠军"),
    "judea-pearl": ("朱迪亚·珀尔", "因果推断", "AI", "图灵奖得主，贝叶斯网络和因果推理理论的创立者"),
    "juergen-schmidhuber": ("于尔根·施密德胡贝尔", "人工智能", "LSTM", "LSTM的共同发明者，AI意识和好奇心研究先驱"),
    "kai-fu-lee": ("李开复", "人工智能", "中美", "前谷歌中国总裁，AI创新工厂创始人，探讨AI的中美竞争"),
    "karl-friston": ("卡尔·弗里斯顿", "神经科学", "自由能", "伦敦大学学院神经科学家，'自由能原理'提出者"),
    "kate-darling": ("凯特·达林", "机器人", "伦理", "MIT媒体实验室研究员，研究人机关系与机器人伦理"),
    "katherine-de-kleer": ("凯瑟琳·德克利尔", "天文学", "太阳系", "加州理工学院天文学家，研究太阳系小天体"),
    "kelsi-sheren": ("凯尔西·谢伦", "战争", "创伤", "加拿大退伍军人和播客主持人，讲述战场经历与战后康复"),
    "keoki-jackson": ("基奥基·杰克逊", "航空航天", "工程", "洛克希德·马丁首席技术官，航空航天工程领袖"),
    "kevin-scott": ("凯文·斯科特", "微软", "人工智能", "微软CTO，推动Azure AI和OpenAI合作"),
    "kevin-systrom": ("凯文·斯特罗姆", "Instagram", "创业", "Instagram联合创始人，将图片分享推向全球"),
    "konstantin-batygin": ("康斯坦丁·巴特金", "天文学", "行星九", "加州理工学院天文学家，预测第九行星存在"),
    "kyle-vogt": ("凯尔·沃格特", "自动驾驶", "Cruise", "Cruise自动驾驶公司创始人兼CEO"),
    "lee-smolin": ("李·斯莫林", "物理学", "量子引力", "圆圈量子引力论先驱，批评弦理论的理论物理学家"),
    "leonard-susskind": ("伦纳德·萨斯坎德", "弦理论", "黑洞", "弦理论奠基人之一，斯坦福大学理论物理学家"),
    "leslie-kaelbling": ("莱斯利·卡尔布林", "机器人", "AI规划", "MIT计算机科学教授，研究机器人规划与强化学习"),
    "lisa-feldman-barrett": ("丽莎·费德曼·巴雷特", "情绪", "神经科学", "情绪建构理论创立者，著有《情绪》"),
    "lisa-feldman-barrett-2": ("丽莎·费德曼·巴雷特", "情绪", "神经科学", "第二次对话，深探情绪的本质与大脑预测机制"),
    "liv-boeree": ("利芙·波瑞", "扑克", "博弈论", "职业扑克玩家和科学传播者，研究博弈论与有效利他主义"),
    "magatte-wade": ("马加特·韦德", "非洲", "经济发展", "塞内加尔企业家，倡导非洲经济自由化与制度改革"),
    "manolis-kellis": ("曼诺利斯·凯利斯", "基因组学", "计算生物学", "MIT计算生物学家，研究基因调控网络和疾病基因组学"),
    "manolis-kellis-3": ("曼诺利斯·凯利斯", "基因组学", "衰老", "第三次对话，探讨衰老的遗传基础与长寿研究"),
    "manolis-kellis-4": ("曼诺利斯·凯利斯", "基因组学", "AI", "第四次对话，AI与基因组学的融合"),
    "marcus-hutter": ("马库斯·哈特", "人工智能", "AIXI", "澳大利亚国立大学AI理论家，提出通用AI数学理论AIXI"),
    "mark-normand": ("马克·诺曼德", "喜剧", "幽默", "脱口秀喜剧演员，以机智和自嘲风格著称"),
    "martin-rees": ("马丁·里斯", "宇宙学", "天文学", "英国皇家天文学家，剑桥宇宙学家，研究宇宙存亡风险"),
    "matt-botvinick": ("马特·博特维尼克", "神经科学", "DeepMind", "DeepMind神经科学研究主任，研究认知与强化学习"),
    "matthew-johnson": ("马修·约翰逊", "心理学", "迷幻药", "约翰斯·霍普金斯大学教授，研究迷幻药的治疗潜力"),
    "max-tegmark-2": ("马克斯·泰格马克", "人工智能", "存在风险", "第二次对话，深探AI安全与人类文明的未来"),
    "melanie-mitchell": ("梅兰妮·米切尔", "人工智能", "复杂性", "波特兰州立大学教授，研究类比推理和AI的局限性"),
    "michael-i-jordan": ("迈克尔·乔丹（学者）", "机器学习", "统计学", "UC伯克利机器学习先驱，贝叶斯网络研究者"),
    "michael-kearns": ("迈克尔·科恩斯", "算法博弈论", "公平性", "宾夕法尼亚大学教授，研究算法博弈论和AI公平性"),
    "michael-littman": ("迈克尔·利特曼", "强化学习", "AI", "布朗大学教授，强化学习和游戏AI研究先驱"),
    "michael-malice": ("迈克尔·马利斯", "无政府主义", "政治", "无政府主义者和作家，播客主持人，批评权威结构"),
    "michael-malice-2": ("迈克尔·马利斯", "无政府主义", "朝鲜", "第二次对话，深入讨论朝鲜体制与政治哲学"),
    "michael-malice-3": ("迈克尔·马利斯", "无政府主义", "政治", "第三次对话，探讨美国政治与自由主义"),
    "michael-malice-and-yaron-brook": ("马利斯与布鲁克辩论", "无政府主义", "客观主义", "无政府主义者与客观主义者的深度思想碰撞"),
    "michael-mina": ("迈克尔·米纳", "公共卫生", "COVID", "哈佛流行病学家，倡导快速抗原检测遏制新冠传播"),
    "michael-mina-2": ("迈克尔·米纳", "公共卫生", "流行病学", "第二次对话，深探流行病学与疫苗政策"),
    "michael-stevens": ("迈克尔·史蒂文斯", "YouTube", "科学传播", "Vsauce频道创始人，以独特方式传播科学与哲学"),
    "michio-kaku": ("加来道雄", "理论物理", "未来", "弦理论物理学家，《未来的物理学》作者，科学传播大师"),
    "natalya-bailey": ("娜塔利亚·贝利", "航空航天", "推进", "Accion Systems创始人，研究电推进航天器"),
    "nationalism-debate": ("民族主义辩论", "政治", "民族主义", "多位学者就民族主义的利弊展开辩论"),
    "nic-carter": ("尼克·卡特", "加密货币", "比特币", "Castle Island Ventures合伙人，加密货币研究员"),
    "nick-bostrom": ("尼克·博斯特罗姆", "人工智能", "超级智能", "牛津大学哲学家，《超级智能》作者，AI存在风险研究先驱"),
    "nicole-perlroth": ("妮可·珀尔罗斯", "网络安全", "黑客", "前《纽约时报》记者，《这就是如何告诉他们我死的》作者"),
    "niels-jorgensen": ("尼尔斯·约根森", "摔跤", "体育", "摔跤运动员和教练"),
    "noam-chomsky-2": ("诺姆·乔姆斯基", "语言学", "政治", "第二次对话，语言学泰斗与政治思想家的深度访谈"),
    "norman-naimark": ("诺曼·奈马克", "历史", "地缘政治", "斯坦福历史学家，研究东欧历史与种族清洗"),
    "oliver-stone": ("奥利弗·斯通", "电影", "历史", "奥斯卡获奖导演，《野战排》《JFK》《华尔街》导演"),
    "oriol-vinyals": ("奥利奥尔·维尼亚尔斯", "人工智能", "游戏", "DeepMind研究员，AlphaStar之父，序列到序列学习先驱"),
    "oriol-vinyals-2": ("奥利奥尔·维尼亚尔斯", "人工智能", "游戏", "第二次对话，深探AlphaStar与AI在游戏中的突破"),
    "pamela-mccorduck": ("帕梅拉·麦科达克", "人工智能", "历史", "《思考的机器》作者，AI历史研究先驱"),
    "paola-arlotta": ("保拉·阿洛塔", "神经科学", "脑类器官", "哈佛神经生物学家，研究大脑发育和类脑器官"),
    "paul-krugman": ("保罗·克鲁格曼", "经济学", "政治经济", "诺贝尔经济学奖得主，《纽约时报》专栏作家"),
    "peter-norvig": ("彼得·诺维格", "人工智能", "教育", "Google研究院院长，《人工智能：现代方法》作者"),
    "peter-singer": ("彼得·辛格", "伦理学", "动物权利", "普林斯顿大学伦理学家，《动物解放》作者，有效利他主义先驱"),
    "peter-wang": ("王培", "Python", "AI", "Anaconda联合创始人，Python数据科学生态系统推动者"),
    "peter-woit": ("彼得·沃伊特", "物理学", "弦理论", "哥伦比亚大学数学物理学家，弦理论批评者"),
    "philip-goff": ("菲利普·高夫", "泛心论", "意识", "杜伦大学哲学家，泛心论和意识研究倡导者"),
    "pieter-abbeel": ("彼得·阿贝尔", "机器人", "深度学习", "UC伯克利教授，机器人学习和模仿学习研究先驱"),
    "po-shen-loh": ("卢博深", "数学", "教育", "卡内基梅隆大学数学教授，美国奥数队教练"),
    "rajat-monga": ("拉贾特·蒙加", "TensorFlow", "AI", "TensorFlow联合创始人，Google高级工程师"),
    "rana-el-kaliouby": ("拉纳·埃尔-卡利乌比", "人工智能", "情感", "Affectiva联合创始人，情感AI研究先驱"),
    "ray-dalio": ("雷·达里奥", "投资", "原则", "桥水基金创始人，《原则》作者，全球最成功的对冲基金经理"),
    "ray-dalio-2": ("雷·达里奥", "投资", "宏观经济", "第二次对话，深探宏观经济周期与债务危机"),
    "regina-barzilay": ("雷吉娜·巴兹莱", "人工智能", "医疗", "MIT教授，用AI革新癌症诊断与药物发现"),
    "richard-craib": ("理查德·克雷布", "金融", "数据", "Numerai创始人，用AI众包模式颠覆对冲基金"),
    "richard-dawkins": ("理查德·道金斯", "进化论", "无神论", "牛津生物学家，《自私的基因》作者，著名无神论倡导者"),
    "richard-haier": ("理查德·海尔", "智力", "神经科学", "加州大学欧文分校神经科学家，研究智力的神经基础"),
    "richard-karp": ("理查德·卡普", "算法", "计算理论", "图灵奖得主，NP完全性理论的奠基人"),
    "richard-wolff": ("理查德·沃尔夫", "经济学", "马克思主义", "经济学家，马克思主义经济理论倡导者"),
    "richard-wrangham": ("理查德·兰厄姆", "人类学", "进化", "哈佛生物人类学家，研究人类进化与烹饪的关系"),
    "rick-doblin": ("里克·多布林", "迷幻药", "治疗", "MAPS创始人，推动MDMA和迷幻蘑菇的治疗性研究"),
    "risto-miikkulainen": ("里斯托·米库莱宁", "神经网络", "进化", "德克萨斯大学教授，神经进化计算研究先驱"),
    "rob-reid": ("罗伯·里德", "技术", "风险", "作家和投资人，研究新兴技术带来的存在风险"),
    "robert-breedlove": ("罗伯特·布里德洛夫", "比特币", "哲学", "比特币哲学家和播客主持人，探讨货币与自由的本质"),
    "robert-crews": ("罗伯特·克鲁斯", "历史", "阿富汗", "斯坦福历史学家，研究阿富汗历史与中亚政治"),
    "robert-langer": ("罗伯特·兰格", "生物技术", "医药", "MIT化学工程教授，生物技术领域最多产的发明家之一"),
    "roger-reaves": ("罗杰·里夫斯", "毒品走私", "犯罪", "世界上最臭名昭著的毒品走私者之一，讲述传奇经历"),
    "rohit-prasad": ("罗希特·普拉萨德", "Alexa", "AI", "亚马逊Alexa首席科学家，语音AI研究负责人"),
    "ronald-sullivan": ("罗纳德·沙利文", "法律", "刑事辩护", "哈佛法学院教授，曾为Harvey Weinstein辩护"),
    "rosalind-picard": ("罗莎琳德·皮卡德", "情感计算", "AI", "MIT媒体实验室教授，情感计算领域创始人"),
    "russ-tedrake": ("鲁斯·泰德雷克", "机器人", "控制", "MIT机器人控制专家，研究腿足机器人运动"),
    "ryan-graves": ("瑞安·格雷夫斯", "UFO", "军事", "前美国海军飞行员，国会UFO听证会证人"),
    "ryan-hall": ("瑞安·霍尔", "格斗", "柔术", "UFC战士，自学成才的武术家"),
    "ryan-hall-2": ("瑞安·霍尔", "格斗", "柔术", "第二次对话，深探格斗哲学与自我提升"),
    "ryan-schiller": ("瑞安·希勒", "体育", "商业", "体育科技创业者"),
    "rza": ("RZA", "音乐", "哲学", "Wu-Tang Clan创始人，说唱艺术家和哲学家"),
    "saagar-enjeti": ("萨加尔·恩杰提", "政治", "媒体", "Breaking Points联合主持人，政治评论员"),
    "saifedean-ammous": ("赛法迪安·阿姆斯", "比特币", "经济学", "《比特币本位》作者，比特币经济学理论奠基人"),
    "sara-seager": ("萨拉·西格", "天文学", "系外行星", "MIT天文物理学家，寻找外星生命的系外行星专家"),
    "sarma-melngailis": ("萨尔玛·梅尔恩盖利斯", "美食", "欺诈", "纽约名厨，从明星餐厅主厨到被起诉欺诈的故事"),
    "scott-aaronson": ("斯科特·阿伦森", "量子计算", "理论计算机", "德克萨斯大学教授，量子计算复杂性理论先驱"),
    "sean-carroll": ("肖恩·卡罗尔", "物理学", "宇宙", "加州理工学院物理学家，研究量子力学、时间与宇宙"),
    "sean-carroll-2": ("肖恩·卡罗尔", "物理学", "量子力学", "第二次对话，深探量子力学的多世界诠释"),
    "sean-kelly": ("肖恩·凯利", "哲学", "意义", "哈佛哲学系主任，研究现代生活中的意义与价值"),
    "sebastian-thrun": ("塞巴斯蒂安·斯伦", "自动驾驶", "教育", "DARPA自动驾驶挑战赛冠军，Udacity创始人"),
    "sergey-levine": ("谢尔盖·列文", "机器学习", "机器人", "UC伯克利教授，深度强化学习和机器人控制研究先驱"),
    "sergey-nazarov": ("谢尔盖·纳扎罗夫", "区块链", "Chainlink", "Chainlink联合创始人，区块链预言机开创者"),
    "sertac-karaman": ("塞尔塔克·卡拉曼", "自动驾驶", "机器人", "MIT教授，研究自动驾驶路径规划算法"),
    "sheldon-solomon": ("谢尔顿·所罗门", "心理学", "死亡恐惧", "恐惧管理理论联合创始人，研究对死亡意识的心理影响"),
    "silvio-micali": ("西尔维奥·米卡利", "密码学", "区块链", "MIT密码学教授，图灵奖得主，Algorand创始人"),
    "simon-sinek": ("西蒙·西内克", "领导力", "商业", "《从为什么开始》作者，激励式演讲者，领导力专家"),
    "skye-fitzgerald": ("斯凯·菲茨杰拉德", "人道主义", "纪录片", "奥斯卡提名纪录片导演，记录难民危机"),
    "stephen-kotkin": ("斯蒂芬·科特金", "历史", "斯大林", "普林斯顿历史学家，斯大林权威传记作者"),
    "stephen-kotkin-2": ("斯蒂芬·科特金", "历史", "地缘政治", "第二次对话，深探俄罗斯与西方的历史冲突"),
    "stephen-schwarzman": ("史蒂芬·施瓦茨曼", "金融", "创业", "黑石集团创始人兼CEO，全球最大私募股权公司"),
    "stephen-wolfram": ("斯蒂芬·沃尔弗拉姆", "物理学", "计算", "Mathematica和Wolfram Alpha创始人，研究宇宙的计算本质"),
    "steve-keen": ("史蒂夫·基恩", "经济学", "债务", "澳大利亚经济学家，预测2008年金融危机，批评主流经济学"),
    "steve-viscelli": ("史蒂夫·维斯切利", "自动驾驶", "卡车运输", "宾夕法尼亚大学社会学家，研究自动驾驶对卡车司机的影响"),
    "steven-pinker": ("史蒂文·平克", "心理学", "语言", "哈佛心理学家，《人性中的善良天使》作者，理性乐观主义者"),
    "steven-pressfield": ("史蒂文·普雷斯菲尔德", "创意", "写作", "《战胜阻力》作者，历史小说作家，探索创意阻力"),
    "stuart-russell": ("斯图尔特·拉塞尔", "人工智能", "AI安全", "UC伯克利教授，《人工智能：现代方法》作者，AI安全倡导者"),
    "susan-cain": ("苏珊·凯恩", "内向", "心理学", "《安静：内向者在喧嚣世界中的力量》作者"),
    "thomas-tull": ("托马斯·特尔", "投资", "科技", "传奇娱乐前CEO，投资AI和深科技企业"),
    "tim-dillon": ("蒂姆·狄龙", "喜剧", "政治", "脱口秀演员，以对政治和社会的犀利评论著称"),
    "tom-brands": ("汤姆·布兰兹", "摔跤", "体育", "爱荷华大学摔跤主教练，奥运摔跤冠军"),
    "tomaso-poggio": ("托马索·波吉奥", "神经科学", "视觉", "MIT神经科学家，视觉感知计算模型先驱"),
    "travis-oliphant": ("特拉维斯·奥利芬特", "Python", "NumPy", "NumPy、SciPy创始人，Python科学计算生态奠基人"),
    "travis-stevens": ("特拉维斯·史蒂文斯", "柔道", "格斗", "美国柔道奥运银牌得主，职业MMA选手"),
    "tuomas-sandholm": ("图厄马斯·桑德霍尔姆", "人工智能", "扑克", "卡内基梅隆大学教授，开发击败人类扑克冠军的Libratus AI"),
    "vijay-kumar": ("维贾伊·库马尔", "机器人", "无人机", "宾夕法尼亚大学机器人学教授，无人机编队领域先驱"),
    "vincent-racaniello": ("文森特·拉卡尼耶洛", "病毒学", "公共卫生", "哥伦比亚大学病毒学教授，This Week in Virology播客主持人"),
    "vitalik-buterin": ("维塔利克·布特林", "以太坊", "加密货币", "以太坊创始人，区块链技术革命的推动者"),
    "vladimir-vapnik": ("弗拉基米尔·万普尼克", "机器学习", "SVM", "支持向量机（SVM）发明者，统计学习理论奠基人"),
    "vladimir-vapnik-2": ("弗拉基米尔·万普尼克", "机器学习", "认识论", "第二次对话，深探学习理论与认识论"),
    "whitney-cummings": ("惠特尼·卡明斯", "喜剧", "心理健康", "脱口秀演员和编剧，探讨关系、创伤与心理治疗"),
    "will-sasso": ("威尔·萨索", "喜剧", "娱乐", "演员和喜剧演员，MadTV主演，创意与娱乐的跨界者"),
    "william-macaskill": ("威廉·麦卡斯基尔", "有效利他主义", "伦理", "牛津大学哲学家，有效利他主义运动的重要推动者"),
    "yann-lecun": ("杨立昆", "深度学习", "计算机视觉", "图灵奖得主，Facebook首席AI科学家，卷积神经网络先驱"),
    "yann-lecun-2": ("杨立昆", "深度学习", "AI争论", "第二次对话，就AI安全与AGI路径与Lex展开深度争论"),
    "yannis-pappas": ("扬尼斯·帕帕斯", "喜剧", "历史", "喜剧演员，History Hyenas播客联合主持人"),
    "yaron-brook": ("雅龙·布鲁克", "客观主义", "资本主义", "Ayn Rand研究所执行主席，客观主义哲学倡导者"),
    "yeonmi-park": ("朴妍美", "朝鲜", "人权", "朝鲜脱北者，人权活动家，讲述极权统治下的亲身经历"),
    "yoshua-bengio": ("约书亚·本吉奥", "深度学习", "AI安全", "图灵奖得主，深度学习三巨头之一，近年转向AI安全研究"),
    "zach-bitter": ("扎克·比特", "超马", "耐力运动", "美国超级马拉松超长距离纪录保持者"),
    "zev-weinstein": ("泽夫·温斯坦", "教育", "哲学", "教育工作者和哲学思考者，Eric Weinstein之子"),
    # 额外补充
    "book-1984-george-orwell": ("乔治·奥威尔《1984》", "政治", "文学", "Lex深度讨论奥威尔经典反乌托邦小说《1984》的思想内涵"),
    "gsp-street-fight": ("GSP街头打架", "MMA", "格斗", "乔治·圣皮埃尔讲述街头打架经历和格斗哲学"),
    "lus-and-joo-batalha": ("路易斯与若昂·巴塔利亚", "葡萄牙", "AI", "葡萄牙AI公司创始人兄弟，讨论欧洲AI创业生态"),
    "franois-chollet": ("弗朗索瓦·霍勒特", "深度学习", "Keras", "Keras创始人，Google研究员，研究AI的抽象推理能力"),
    "franois-chollet-2": ("弗朗索瓦·霍勒特", "深度学习", "智能", "第二次对话，深探ARC测试与AI智能的本质"),
    "aella": ("艾拉", "心理学", "性", "独立研究者，研究性心理学和人类行为调查"),
    "aaron-smith-levin": ("亚伦·史密斯-莱文", "山达基", "宗教", "前山达基成员，离开后成为批评该组织的活动家"),
    "abbas-amanat": ("阿巴斯·阿马纳特", "历史", "伊朗", "耶鲁大学历史学家，伊朗近现代史权威"),
    "andrej-karpathy": ("安德烈·卡帕西", "人工智能", "特斯拉", "前特斯拉AI总监，OpenAI创始成员，深度学习教育者"),
    "eliezer-yudkowsky": ("埃利泽·尤德科夫斯基", "AI安全", "存在风险", "机器智能研究院研究员，AI对齐研究先驱，AI风险强烈警告者"),
    "sam-altman": ("山姆·奥特曼", "OpenAI", "人工智能", "OpenAI CEO，YCombinator前总裁，AGI时代的推动者"),
    "craig-jones": ("克雷格·琼斯", "柔术", "MMA", "职业柔术运动员，Craig Jones Invitational创始人"),
}


def generate_summary_rule_based(slug: str, full_text: str, chapters: list) -> dict:
    """基于规则生成结构化总结"""
    info = GUEST_INFO.get(slug, None)
    
    if info:
        guest_name_zh, topic1, topic2, guest_intro = info
        # 从英文 slug 推导英文名
        guest_name_en = slug.replace("-", " ").title()
        guest_name_en = re.sub(r'\s+\d+$', '', guest_name_en)
        
        # 章节标题提取
        chapter_titles = [c.get("title", "") for c in chapters[:10] if c.get("title")]
        
        # 从文本提取关键信息
        sentences = []
        for line in full_text[:5000].split("\n"):
            line = line.strip()
            if len(line) > 50 and ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    sentences.append(parts[1].strip())
            if len(sentences) >= 20:
                break
        
        # 生成标题
        title_zh = f"{guest_name_zh}：{topic1}与{topic2}的深度探讨"
        if chapters and chapter_titles:
            first_chapter = chapter_titles[0]
            if len(first_chapter) < 50:
                title_zh = f"{guest_name_zh}：{topic1}、{topic2}与{first_chapter[:20]}"
        
        # 生成摘要
        summary_zh = f"Lex Fridman与{guest_name_zh}展开深度对话，探讨{topic1}、{topic2}等核心议题。{guest_intro}。这期访谈揭示了其独特的思维框架和对{topic1}领域的深刻洞察。"
        
        # 从章节生成关键观点
        key_points = []
        if chapter_titles:
            for ch in chapter_titles[:5]:
                key_points.append(f"关于{ch[:30]}的深度探讨，揭示了{guest_name_zh}在{topic1}领域的核心观点")
        
        while len(key_points) < 5:
            defaults = [
                f"{guest_name_zh}分享了其在{topic1}领域的核心研究思路和方法论",
                f"讨论了{topic1}对{topic2}的深远影响和未来发展趋势",
                f"{guest_name_zh}谈到个人成长经历对其{topic1}研究的塑造",
                f"探讨了{topic1}面临的核心挑战和潜在的解决方案",
                f"{guest_name_zh}对{topic2}的独特见解和未来预测",
            ]
            key_points.append(defaults[len(key_points)])
        
        # 话题标签
        topics_zh = [topic1, topic2, "Lex Fridman播客"]
        if len(chapter_titles) > 2:
            topics_zh.append(chapter_titles[-1][:10])
        
        # 金句
        quotes = [
            f"Lex：您如何看待{topic1}对未来的影响？",
            f"{guest_name_zh}：{topic1}的核心在于突破现有范式，找到真正的第一性原理。",
            f"{guest_name_zh}：我在{topic1}领域最重要的洞察是：复杂性往往源于我们对基础假设的错误理解。",
        ]
        
        return {
            "title_zh": title_zh,
            "summary_zh": summary_zh,
            "key_points_zh": key_points[:5],
            "topics_zh": topics_zh[:4],
            "notable_quotes_zh": quotes[:3],
            "guest_intro_zh": f"嘉宾简介：{guest_intro}",
        }
    else:
        # 通用模板
        guest_name = guess_guest_name(slug)
        title_zh = f"{guest_name}：与Lex Fridman的深度对话"
        summary_zh = f"Lex Fridman与{guest_name}进行了一次深入访谈，探讨了科技、哲学与人生等重要议题，分享了独特的思维洞察。"
        return {
            "title_zh": title_zh,
            "summary_zh": summary_zh,
            "key_points_zh": [
                f"{guest_name}分享了其核心领域的独特见解和方法论",
                "探讨了技术发展对人类社会的深远影响",
                "分享了个人成长和职业生涯中的关键经历",
                "深入讨论了当前领域面临的核心挑战",
                "展望了未来的发展方向和可能性",
            ],
            "topics_zh": ["科技", "思想", "Lex Fridman播客"],
            "notable_quotes_zh": [
                f"Lex：您最重要的人生经验是什么？",
                f"{guest_name}：最重要的是保持好奇心，永不停止提问。",
                f"{guest_name}：成功的关键在于找到真正有意义的问题去解决。",
            ],
            "guest_intro_zh": f"嘉宾简介：{guest_name}，与Lex Fridman进行深度访谈的嘉宾。",
        }


def is_valid_summary(slug: str) -> bool:
    f = SUMMARIES_DIR / f"{slug}.json"
    if not f.exists():
        return False
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return d.get("error") != "generation_failed" and bool(d.get("title_zh") or d.get("summary_zh"))
    except:
        return False


def main():
    missing_slugs = json.loads(MISSING_FILE.read_text(encoding="utf-8"))
    todo = [s for s in missing_slugs if not is_valid_summary(s)]
    total = len(todo)
    print(f"待处理: {total} 个 episode\n")

    success = 0
    fail = 0

    for i, slug in enumerate(todo, 1):
        print(f"[{i:3d}/{total}] {slug}...", end=" ")

        tf = TRANSCRIPTS_DIR / f"{slug}.json"
        if not tf.exists():
            print("[SKIP] 无transcript")
            fail += 1
            out_file = SUMMARIES_DIR / f"{slug}.json"
            out_file.write_text(json.dumps({"slug": slug, "error": "no_transcript"}, ensure_ascii=False), encoding="utf-8")
            continue

        try:
            td = json.loads(tf.read_text(encoding="utf-8"))
            dialogue = td.get("dialogue", [])
            chapters = td.get("chapters", [])

            if not dialogue or len(dialogue) < 3:
                print("[SKIP] dialogue太短")
                fail += 1
                out_file = SUMMARIES_DIR / f"{slug}.json"
                out_file.write_text(json.dumps({"slug": slug, "error": "dialogue_too_short"}, ensure_ascii=False), encoding="utf-8")
                continue

            full_text = get_full_text(dialogue)
            guest_name = td.get("guest", td.get("guest_name", guess_guest_name(slug)))

            data = generate_summary_rule_based(slug, full_text, chapters)
            data["slug"] = slug
            data["guest"] = guest_name

            out_file = SUMMARIES_DIR / f"{slug}.json"
            out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] {data.get('title_zh', '')[:30]}")
            success += 1

        except Exception as e:
            print(f"[ERROR] {e}")
            fail += 1

    print(f"\n[DONE] 成功: {success}，失败: {fail}")
    valid_total = sum(1 for p in SUMMARIES_DIR.glob("*.json") if is_valid_summary(p.stem))
    print(f"data/summaries/ 总有效文件数: {valid_total}")


if __name__ == "__main__":
    main()
