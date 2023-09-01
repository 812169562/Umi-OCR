# ===============================================
# =============== OCR - 任务管理器 ===============
# ===============================================

"""
一种任务管理器为全局单例，不同标签页要执行同一种任务，要访问对应的任务管理器。
任务管理器中有一个引擎API实例，所有任务均使用该API。
标签页可以向任务管理器提交一组任务队列，其中包含了每一项任务的信息，及总体的参数和回调。
"""

from ..ocr.api import getApiOcr, isApiOcr
from .mission import Mission
from ..ocr.tbpu import Merge as tbpuMerge

from PIL import Image
from io import BytesIO


class __MissionOcrClass(Mission):
    def __init__(self):
        super().__init__()
        self.__apiKey = ""  # 当前api类型
        self.__api = None  # 当前引擎api对象

    # ========================= 【重载】 =========================

    def addMissionList(self, msnInfo, msnList):  # 添加任务列表
        # 实例化 tbpu 文本后处理模块
        msnInfo["tbpu"] = []
        argd = msnInfo["argd"]
        if "tbpu.merge" in argd:
            # 段落合并
            if argd["tbpu.merge"] in tbpuMerge:
                msnInfo["tbpu"].append(tbpuMerge[argd["tbpu.merge"]]())
        print("== 创建 tbpu.merge ", msnInfo["tbpu"])
        return super().addMissionList(msnInfo, msnList)

    def msnPreTask(self, msnInfo):  # 用于更新api和参数
        # 检查API对象
        if not self.__api:
            return "[Error] MissionOCR: API object is None."
        # 检查参数更新
        msg = self.__api.start(msnInfo["argd"])
        if msg.startswith("[Error]"):
            return msg  # 更新失败，结束该队列
        else:
            return ""  # 更新成功 TODO: continue

    def msnTask(self, msnInfo, msn):  # 执行msn
        if "path" in msn:
            res = self.__api.runPath(msn["path"])
        elif "bytes" in msn:
            res = self.__api.runBytes(msn["bytes"])
        # elif "clipboard" in msn:
        #     res = self.__api.runClipboard()
        else:
            res = {
                "code": 901,
                "data": f"[Error] Unknown task type.\n【异常】未知的任务类型。\n{str(msn)[:100]}",
            }
        # 执行 tbpu
        if res["code"] == 100:
            if msnInfo["tbpu"]:
                imgInfo = {"w": 0, "h": 0}
                if "path" in msn:
                    with Image.open(msn["path"]) as image:
                        width, height = image.size
                        imgInfo = {"w": width, "h": height}
                elif "bytes" in msn:
                    imgFile = BytesIO(msn["bytes"])
                    with Image.open(imgFile) as image:
                        width, height = image.size
                        imgInfo = {"w": width, "h": height}
                else:
                    print("【Warning】tbpu未获得图片信息！")
                for tbpu in msnInfo["tbpu"]:
                    res["data"] = tbpu.run(res["data"], imgInfo)
        return res

    # ========================= 【qml接口】 =========================

    def getStatus(self):  # 返回当前状态
        return {
            "apiKey": self.__apiKey,
            "missionListsLength": self.getMissionListsLength(),
        }

    def setApi(self, info):  # 设置api
        # 成功返回 [Success] ，失败返回 [Error] 开头的字符串
        apiKey = info["ocr.api"]
        # 如果api对象已启动，则先停止
        if self.__api:
            self.__api.stop()
        # 获取新api对象
        res = getApiOcr(apiKey, info)
        # 成功
        if isApiOcr(res):
            self.__api = res
            self.__apiKey = apiKey
            return "[Success]"
        # 失败
        else:
            self.__apiKey = ""
            self.__api = None
            if type(res) == str:
                return res
            return "[Error] MissionOCR Failed to setApi, unknown reason."

    def getApiInfo(self):  # 获取当前API的额外信息
        return self.__api.getApiInfo()


# 全局 OCR任务管理器
MissionOCR = __MissionOcrClass()
