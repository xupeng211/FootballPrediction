<template>
  <div id="app">
    <!-- Layout System -->
    <component :is="layoutComponent">
      <router-view />
    </component>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'

const route = useRoute()

const layoutComponent = computed(() => {
  switch (route.meta.layout) {
    case 'auth':
      return AuthLayout
    case 'main':
    default:
      return MainLayout
  }
})
</script>