import type { PlanningProject } from './model'

export const mockProjects: PlanningProject[] = [
  {
    id: 'project-kyushu',
    title: '九州轻量行程',
    status: 'board_created',
    chatSessionId: 'session-kyushu',
    tripBoardId: 'trip-kyushu',
    updatedAt: '今天 09:20',
    intake: {
      destination: '日本 / 九州',
      duration: '9 月 · 5-6 天',
      travelers: 2,
      budget: '¥8,000-10,000',
      preferences: ['温泉', '美食', '自然', '不赶'],
    },
    messages: [
      {
        id: 'm1',
        role: 'user',
        content:
          '我想 9 月从上海出发去日本 5-6 天，两个人，预算 8000-10000，想要温泉、美食、自然风景，不想每天太赶。',
        createdAt: '09:10',
      },
      {
        id: 'm2',
        role: 'assistant',
        content: '信息够了，可以开始生成 Trip Board。',
        createdAt: '09:12',
      },
    ],
  },
  {
    id: 'project-family',
    title: '亲子少走路周末',
    status: 'collecting',
    chatSessionId: 'session-family',
    updatedAt: '昨天 21:14',
    intake: {
      destination: '待确认',
      duration: '周末 2-3 天',
      travelers: 3,
      preferences: ['亲子', '少走路'],
    },
    messages: [
      {
        id: 'm3',
        role: 'assistant',
        content: '你想偏城市轻松，还是自然风景多一点？',
        createdAt: '21:13',
      },
      {
        id: 'm4',
        role: 'user',
        content: '小朋友 6 岁，希望不要太赶，也不要每天换酒店。',
        createdAt: '21:14',
      },
    ],
  },
  {
    id: 'project-seoul',
    title: '首尔短假',
    status: 'ready_to_start',
    chatSessionId: 'session-seoul',
    updatedAt: '周一 18:02',
    intake: {
      destination: '韩国 / 首尔',
      duration: '4 天',
      travelers: 2,
      budget: '¥6,000',
      preferences: ['咖啡', '购物', '不换酒店'],
    },
    messages: [
      {
        id: 'm5',
        role: 'assistant',
        content: '信息够了，可以开始生成 Trip Board。',
        createdAt: '18:02',
      },
    ],
  },
]
