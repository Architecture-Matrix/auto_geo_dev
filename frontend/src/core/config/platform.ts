/**
 * 平台配置
 * 我用这个来管理各平台的配置信息！
 */

export interface PlatformConfig {
  // 基础信息
  id: string
  name: string
  code: string
  icon: string
  color: string

  // 功能开关
  features: {
    article: boolean
    video: boolean
    image: boolean
    draft: boolean
    schedule: boolean
  }

  // 认证配置
  auth: {
    type: 'qrcode' | 'password' | 'oauth'
    loginUrl: string
    checkLoginInterval: number
    maxWaitTime: number
  }

  // 发布配置
  publish: {
    entryUrl: string
    selectors: {
      title: string
      content: string
      submit: string
    }
    waitTimes: {
      afterLoad: number
      afterFill: number
      afterSubmit: number
    }
  }

  // 限制配置
  limits: {
    titleLength: [number, number]
    contentLength: [number, number]
    imageCount: number
  }
}

/**
 * 当前支持的平台配置
 * 我设计了一个可扩展的配置结构！
 */
export const PLATFORMS: Record<string, PlatformConfig> = {
  zhihu: {
    id: 'zhihu',
    name: '知乎',
    code: 'ZH',
    icon: 'zhihu.svg',
    color: '#0084FF',
    features: { article: true, video: true, image: true, draft: true, schedule: false },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.zhihu.com/signin',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://zhuanlan.zhihu.com/write',
      selectors: {
        title: 'input[placeholder*="请输入标题"], .Input input',
        content: '.public-DraftStyleDefault-block, [contenteditable="true"]',
        submit: '.PublishButton, button[class*="Publish"]',
      },
      waitTimes: { afterLoad: 2000, afterFill: 500, afterSubmit: 3000 },
    },
    limits: { titleLength: [1, 100], contentLength: [0, 100000], imageCount: 100 },
  },
  baijiahao: {
    id: 'baijiahao',
    name: '百家号',
    code: 'BJH',
    icon: 'baijiahao.svg',
    color: '#E53935',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://baijiahao.baidu.com/builder/rc/static/login/index',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://baijiahao.baidu.com/builder/rc/edit/index',
      selectors: {
        title: 'input[placeholder*="标题"], input[class*="title"]',
        content: '.editor-body, #ueditor_textarea, [contenteditable="true"]',
        submit: '.submit-btn, button[class*="submit"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 30], contentLength: [0, 50000], imageCount: 100 },
  },
  sohu: {
    id: 'sohu',
    name: '搜狐号',
    code: 'SOHU',
    icon: 'sohu.svg',
    color: '#FF6B00',
    features: { article: true, video: false, image: true, draft: true, schedule: true },
    auth: {
      type: 'password',
      loginUrl: 'https://mp.sohu.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.sohu.com/upload/article',
      selectors: {
        title: '#title, input[name="title"]',
        content: '#ueditor_textarea, iframe[id*="ueditor"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 2000, afterFill: 1000, afterSubmit: 3000 },
    },
    limits: { titleLength: [5, 30], contentLength: [0, 50000], imageCount: 50 },
  },
  toutiao: {
    id: 'toutiao',
    name: '头条号',
    code: 'TT',
    icon: 'toutiao.svg',
    color: '#333333',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.toutiao.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.toutiao.com/profile/article/article_edit',
      selectors: {
        title: 'input[field="title"], input[name="title"]',
        content: '.article-container, [class*="editor"]',
        submit: '.submit-btn, button[class*="submit"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 30], contentLength: [0, 50000], imageCount: 100 },
  },
  wenku: {
    id: 'wenku',
    name: '百度文库',
    code: 'WK',
    icon: 'wenku.svg',
    color: '#2932E1',
    features: { article: true, video: false, image: false, draft: true, schedule: false },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://passport.baidu.com/v2/?login&tpl=wenku',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://wenku.baidu.com/user/upload',
      selectors: {
        title: 'input[placeholder*="标题"], .doc-title-input',
        content: '.doc-uploader, .upload-area',
        submit: '.submit-btn, .upload-btn',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [1, 50], contentLength: [0, 100000], imageCount: 0 },
  },
  penguin: {
    id: 'penguin',
    name: '企鹅号',
    code: 'OM',
    icon: 'penguin.svg',
    color: '#1E8AE8',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://om.qq.com/userAuth/index',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://om.qq.com/article/articlePublish',
      selectors: {
        title: 'input[placeholder*="标题"], #title',
        content: '#ueditor_0, .editor-container',
        submit: '.btn-publish, .submit',
      },
      waitTimes: { afterLoad: 3000, afterFill: 1000, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 30], contentLength: [0, 50000], imageCount: 50 },
  },
  weixin: {
    id: 'weixin',
    name: '微信公众号',
    code: 'WX',
    icon: 'weixin.svg',
    color: '#07C160',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.weixin.qq.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit',
      selectors: {
        title: '#title, .title-input',
        content: '#ueditor_0, .editor_area',
        submit: '#js_submit, .btn_submit',
      },
      waitTimes: { afterLoad: 3000, afterFill: 1000, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 64], contentLength: [0, 50000], imageCount: 50 },
  },
  wangyi: {
    id: 'wangyi',
    name: '网易号',
    code: 'WY',
    icon: 'wangyi.svg',
    color: '#E60026',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.163.com/login.html',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.163.com/admin/article/publish',
      selectors: {
        title: 'input[name="title"]',
        content: '#editor',
        submit: '.submit-btn',
      },
      waitTimes: { afterLoad: 3000, afterFill: 1000, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 30], contentLength: [0, 50000], imageCount: 50 },
  },
  zijie: {
    id: 'zijie',
    name: '字节号',
    code: 'ZJ',
    icon: 'zijie.svg',
    color: '#FA2A2D',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.toutiao.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.toutiao.com/profile/article/article_edit',
      selectors: {
        title: 'input[field="title"], input[name="title"]',
        content: '.article-container, [class*="editor"]',
        submit: '.submit-btn, button[class*="submit"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 30], contentLength: [0, 50000], imageCount: 100 },
  },
  xiaohongshu: {
    id: 'xiaohongshu',
    name: '小红书',
    code: 'XHS',
    icon: 'xiaohongshu.svg',
    color: '#FF2442',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://creator.xiaohongshu.com/login',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://creator.xiaohongshu.com/publish/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 30], contentLength: [0, 50000], imageCount: 50 },
  },
  bilibili: {
    id: 'bilibili',
    name: 'B站专栏',
    code: 'BL',
    icon: 'bilibili.svg',
    color: '#FB7299',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://passport.bilibili.com/login',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://member.bilibili.com/article/post_text',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 100 },
  },
  '36kr': {
    id: '36kr',
    name: '36氪',
    code: '36KR',
    icon: '36kr.svg',
    color: '#FF6A00',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://passport.36kr.com/mo/signin',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://36kr.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  huxiu: {
    id: 'huxiu',
    name: '虎嗅',
    code: 'HX',
    icon: 'huxiu.svg',
    color: '#FF9C41',
    features: { article: true, video: false, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.huxiu.com/passport/login',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://www.huxiu.com/article/post',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  woshipm: {
    id: 'woshipm',
    name: '人人都是产品经理',
    code: 'PM',
    icon: 'woshipm.svg',
    color: '#2ECC71',
    features: { article: true, video: false, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://passport.woshipm.com/login',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://www.woshipm.com/article/post',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  douyin: {
    id: 'douyin',
    name: '抖音',
    code: 'DY',
    icon: 'douyin.svg',
    color: '#000000',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.douyin.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://creator.douyin.com/',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  kuaishou: {
    id: 'kuaishou',
    name: '快手',
    code: 'KS',
    icon: 'kuaishou.svg',
    color: '#FF4500',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://cp.kuaishou.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://cp.kuaishou.com/article/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  video_account: {
    id: 'video_account',
    name: '视频号',
    code: 'WXV',
    icon: 'video_account.svg',
    color: '#07C160',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://channels.weixin.qq.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://channels.weixin.qq.com/post',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  sohu_video: {
    id: 'sohu_video',
    name: '搜狐视频',
    code: 'SHV',
    icon: 'sohu_video.svg',
    color: '#FF6B00',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://tv.sohu.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://tv.sohu.com/upload',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  weibo: {
    id: 'weibo',
    name: '新浪微博',
    code: 'WB',
    icon: 'weibo.svg',
    color: '#E6162D',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://weibo.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://weibo.com/compose',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  haokan: {
    id: 'haokan',
    name: '好看视频',
    code: 'HK',
    icon: 'haokan.svg',
    color: '#2932E1',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://haokan.baidu.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://haokan.baidu.com/upload',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  xigua: {
    id: 'xigua',
    name: '西瓜视频',
    code: 'XG',
    icon: 'xigua.svg',
    color: '#FA2A2D',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://ixigua.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://ixigua.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  jianshu: {
    id: 'jianshu',
    name: '简书号',
    code: 'JS',
    icon: 'jianshu.svg',
    color: '#EA6F5A',
    features: { article: true, video: false, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.jianshu.com/sign_in',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://www.jianshu.com/writer',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  iqiyi: {
    id: 'iqiyi',
    name: '爱奇艺',
    code: 'IQY',
    icon: 'iqiyi.svg',
    color: '#00BE06',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.iqiyi.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.iqiyi.com/upload',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  dayu: {
    id: 'dayu',
    name: '大鱼号',
    code: 'DYU',
    icon: 'dayu.svg',
    color: '#FF6A00',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.dayu.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.dayu.com/article/post',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  acfun: {
    id: 'acfun',
    name: 'AcFun',
    code: 'AC',
    icon: 'acfun.svg',
    color: '#FD4C5D',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.acfun.cn/login',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://member.acfun.cn/article/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  tencent_video: {
    id: 'tencent_video',
    name: '腾讯视频',
    code: 'TXV',
    icon: 'tencent_video.svg',
    color: '#FF6B00',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://v.qq.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://upload.video.qq.com/',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  yidian: {
    id: 'yidian',
    name: '一点号',
    code: 'YD',
    icon: 'yidian.svg',
    color: '#007AFF',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.yidianzixun.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.yidianzixun.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  pipixia: {
    id: 'pipixia',
    name: '皮皮虾',
    code: 'PPX',
    icon: 'pipixia.svg',
    color: '#FF6900',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.pipixia.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://www.pipixia.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  meipai: {
    id: 'meipai',
    name: '美拍',
    code: 'MP',
    icon: 'meipai.svg',
    color: '#1E88E5',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.meipai.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://www.meipai.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  douban: {
    id: 'douban',
    name: '豆瓣',
    code: 'DB',
    icon: 'douban.svg',
    color: '#007722',
    features: { article: true, video: false, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.douban.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://www.douban.com/note',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  kuai_chuan: {
    id: 'kuai_chuan',
    name: '快传号',
    code: 'KC',
    icon: 'kuai_chuan.svg',
    color: '#00BE3B',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://kuai.360.cn/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://kuai.360.cn/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  dafeng: {
    id: 'dafeng',
    name: '大风号',
    code: 'DF',
    icon: 'dafeng.svg',
    color: '#DD2E1B',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.ifeng.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.ifeng.com/article/post',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  xueqiu: {
    id: 'xueqiu',
    name: '雪球号',
    code: 'XQ',
    icon: 'xueqiu.svg',
    color: '#2775CA',
    features: { article: true, video: false, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://xueqiu.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://xueqiu.com/post',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  yiche: {
    id: 'yiche',
    name: '易车号',
    code: 'YC',
    icon: 'yiche.svg',
    color: '#FF6600',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.yiche.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.yiche.com/article/post',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  chejia: {
    id: 'chejia',
    name: '车家号',
    code: 'CJ',
    icon: 'chejia.svg',
    color: '#E60012',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.autohome.com.cn/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.autohome.com.cn/article/post',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  duoduo: {
    id: 'duoduo',
    name: '多多视频',
    code: 'DD',
    icon: 'duoduo.svg',
    color: '#E02E24',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://mp.pinduoduo.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://mp.pinduoduo.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  weishi: {
    id: 'weishi',
    name: '腾讯微视',
    code: 'WS',
    icon: 'weishi.svg',
    color: '#FF6B00',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://weishi.qq.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://weishi.qq.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  mango: {
    id: 'mango',
    name: '芒果TV',
    code: 'MG',
    icon: 'mango.svg',
    color: '#FF7F00',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.mgtv.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://www.mgtv.com/upload',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  ximalaya: {
    id: 'ximalaya',
    name: '喜马拉雅',
    code: 'XMLY',
    icon: 'ximalaya.svg',
    color: '#F84438',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://www.ximalaya.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://www.ximalaya.com/upload',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  meituan: {
    id: 'meituan',
    name: '美团',
    code: 'MT',
    icon: 'meituan.svg',
    color: '#FFBC00',
    features: { article: true, video: false, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://meituan.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://meituan.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  alipay: {
    id: 'alipay',
    name: '支付宝',
    code: 'ZFB',
    icon: 'alipay.svg',
    color: '#1677FF',
    features: { article: true, video: false, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://open.alipay.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://open.alipay.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  douyin_company: {
    id: 'douyin_company',
    name: '抖音企业号',
    code: 'DYC',
    icon: 'douyin_company.svg',
    color: '#000000',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://business.douyin.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://business.douyin.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  douyin_company_lead: {
    id: 'douyin_company_lead',
    name: '抖音企业号（线索版）',
    code: 'DYL',
    icon: 'douyin_company_lead.svg',
    color: '#000000',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: 'https://business.douyin.com/',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: 'https://business.douyin.com/publish',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
  custom: {
    id: 'custom',
    name: '自定义',
    code: 'CUSTOM',
    icon: 'custom.svg',
    color: '#999999',
    features: { article: true, video: true, image: true, draft: true, schedule: true },
    auth: {
      type: 'qrcode',
      loginUrl: '',
      checkLoginInterval: 1000,
      maxWaitTime: 120000,
    },
    publish: {
      entryUrl: '',
      selectors: {
        title: 'input[placeholder*="标题"], .title-input',
        content: '.editor-body, [contenteditable="true"]',
        submit: '.publish-btn, button[class*="publish"]',
      },
      waitTimes: { afterLoad: 3000, afterFill: 500, afterSubmit: 5000 },
    },
    limits: { titleLength: [5, 100], contentLength: [0, 100000], imageCount: 50 },
  },
}

/**
 * 获取平台配置
 */
export function getPlatformConfig(id: string): PlatformConfig | undefined {
  return PLATFORMS[id]
}

/**
 * 获取所有启用的平台
 */
export function getEnabledPlatforms(): PlatformConfig[] {
  return Object.values(PLATFORMS)
}

/**
 * 获取平台图标URL
 */
export function getPlatformIcon(id: string): string {
  return `/src/assets/images/platforms/${id}.svg`
}
