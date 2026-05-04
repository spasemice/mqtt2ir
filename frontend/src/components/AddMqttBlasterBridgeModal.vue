<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useBridgeStore } from '../stores/bridges';
import { useCommonStore } from '../stores/common';

const bridgeStore = useBridgeStore();
const commonStore = useCommonStore();
const { creatingMqttBlasterBridge } = storeToRefs(bridgeStore);

const props = defineProps<{ show: boolean }>();
const emit = defineEmits(['close']);

const bridgeId = ref('');
const name = ref('');
const txTopic = ref('');
const rxTopic = ref('');

const isValid = computed(() => bridgeId.value.trim() && name.value.trim() && txTopic.value.trim() && rxTopic.value.trim());

watch(() => props.show, (v) => {
  if (!v) return;
  bridgeId.value = '';
  name.value = '';
  txTopic.value = '';
  rxTopic.value = '';
});

const handleClose = () => emit('close');

const handleCreate = async () => {
  if (!isValid.value) return;
  try {
    const res = await bridgeStore.createMqttBlasterBridge(bridgeId.value.trim(), name.value.trim(), txTopic.value.trim(), rxTopic.value.trim());
    if (res?.status === 'ok') emit('close');
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'Failed to create MQTT blaster gateway';
    commonStore.addFlashMessage(msg, 'error');
  }
};
</script>

<template>
  <div v-if="show" class="fixed inset-0 !m-0 bg-gray-900/60 flex items-center justify-center z-50 backdrop-blur-sm" @click.self="handleClose">
    <div class="bg-gray-900 rounded-lg shadow-2xl p-6 w-full max-w-md border border-gray-700">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-lg font-semibold">Add MQTT IR Blaster</h2>
        <button class="text-gray-500 hover:text-gray-300 hover:bg-gray-800 p-1 rounded transition-colors" @click="handleClose">
          <i class="mdi mdi-close text-xl" />
        </button>
      </div>

      <div class="space-y-3">
        <div>
          <label class="block text-sm font-semibold mb-1 text-gray-300">Gateway ID</label>
          <input v-model="bridgeId" type="text" class="w-full rounded px-3 py-2" placeholder="livingroom_blaster">
        </div>
        <div>
          <label class="block text-sm font-semibold mb-1 text-gray-300">Name</label>
          <input v-model="name" type="text" class="w-full rounded px-3 py-2" placeholder="Living Room Blaster">
        </div>
        <div>
          <label class="block text-sm font-semibold mb-1 text-gray-300">TX Topic (send)</label>
          <input v-model="txTopic" type="text" class="w-full rounded px-3 py-2" placeholder="zigbee2mqtt/ir_blaster/set/ir_code_to_send">
        </div>
        <div>
          <label class="block text-sm font-semibold mb-1 text-gray-300">RX Topic (learn/received)</label>
          <input v-model="rxTopic" type="text" class="w-full rounded px-3 py-2" placeholder="zigbee2mqtt/ir_blaster">
        </div>
      </div>

      <div class="flex gap-2 pt-5">
        <button class="flex-1 btn btn-secondary" :disabled="creatingMqttBlasterBridge" @click="handleClose">Cancel</button>
        <button class="flex-1 btn btn-primary disabled:opacity-50" :disabled="!isValid || creatingMqttBlasterBridge" @click="handleCreate">
          {{ creatingMqttBlasterBridge ? 'Creating...' : 'Create Gateway' }}
        </button>
      </div>
    </div>
  </div>
</template>
