<template>
  <div class="node">
    <span class="label">{{ label }}:</span>
    <template v-if="typeof value === 'object' && value !== null">
      <div class="nested">
        <json-node v-for="(v, k) in value" :key="k" :value="v" :label="k" />
      </div>
    </template>
    <span v-else class="value">{{ value }}</span>
  </div>
</template>

<script>
export default {
  name: 'JsonNode',
  props: ['value', 'label']
}
</script>

<style scoped>
.node {
  margin-left: 20px;
  margin-top: 5px;
  font-family: monospace;
  font-size: 14px;
}
.label {
  color: var(--accent, #38bdf8);
  font-weight: bold;
  margin-right: 8px;
}
.nested {
  border-left: 1px solid var(--border, #334155);
  padding-left: 10px;
  margin-top: 4px;
}
.value {
  color: #cbd5e1;
}
</style>