<template>
  <n-layout-header class="navbar">
    <div class="navbar-left">
      <div class="logo" @click="router.push('/overview')">
        <n-icon size="28" color="#18a058">
          <Leaf />
        </n-icon>
        <span class="logo-text">筑能智驭</span>
      </div>

      <n-menu
        v-model:value="activeKey"
        mode="horizontal"
        :options="menuOptions"
        @update:value="handleMenuSelect"
      />
    </div>

    <div class="navbar-right">
      <n-space align="center" :size="16">
        <!-- 用户信息 - 点击跳转个人信息 -->
        <div class="user-info" @click="router.push('/home')">
          <n-avatar round size="small" style="background-color: #18a058">
            {{ userStore.userInfo?.name?.charAt(0).toUpperCase() }}
          </n-avatar>
          <span class="username">{{ userStore.userInfo?.name }}</span>
        </div>

        <!-- 退出登录按钮 -->
        <n-button text @click="handleLogout">
          <template #icon>
            <n-icon :component="LogOutOutline" />
          </template>
        </n-button>
      </n-space>
    </div>
  </n-layout-header>
</template>

<script setup lang="ts">
import { ref, h } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useUserStore } from "@/store/user";
import { NIcon, NText } from "naive-ui";
import type { MenuOption } from "naive-ui";
import {
  Leaf,
  Home,
  Analytics,
  AlertCircle,
  LogOutOutline,
  Settings,
  Map
} from "@vicons/ionicons5";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

// 当前激活的菜单项
const activeKey = ref(route.name as string);

// 菜单选项
const menuOptions: MenuOption[] = [
  {
    label: "总览",
    key: "Overview",
    icon: () => h(NIcon, null, { default: () => h(Home) }),
  },
  {
    label: "分析",
    key: "Analysis",
    icon: () => h(NIcon, null, { default: () => h(Analytics) }),
  },
  {
    label: "告警",
    key: "Alarm",
    icon: () => h(NIcon, null, { default: () => h(AlertCircle) }),
  },
  {
    label: "建筑地图",
    key: "BuildingMap",
    icon: () => h(NIcon, null, { default: () => h(Map) }),
  },
  {
    label: "工作区",
    key: "Workspace",
    icon: () => h(NIcon, null, { default: () => h(Settings) }),
  },
];

// 处理菜单选择
const handleMenuSelect = (key: string) => {
  const routeMap: Record<string, string> = {
    Overview: "/overview",
    Analysis: "/analysis",
    Alarm: "/alarm",
    BuildingMap: "/building-map",
    Workspace: "/workspace",
  };

  if (routeMap[key]) {
    router.push(routeMap[key]);
  }
};

// 退出登录
const handleLogout = () => {
  userStore.logoutAction();
  router.push("/login");
};

// 监听路由变化，更新激活状态
router.afterEach((to) => {
  activeKey.value = to.name as string;
});
</script>

<style scoped lang="scss">
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
  background: var(--card-bg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition:
    background 0.3s ease,
    box-shadow 0.3s ease;
  z-index: 1000;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: opacity 0.3s ease;

  &:hover {
    opacity: 0.8;
  }

  .logo-text {
    width: 80px;
    font-size: 18px;
    font-weight: bold;
    color: var(--text-primary);
    transition: color 0.3s ease;
  }
}

.navbar-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.3s ease;

  &:hover {
    background: rgba(0, 0, 0, 0.05);
  }

  .username {
    font-size: 14px;
    color: var(--text-primary);
    transition: color 0.3s ease;
  }
}
</style>