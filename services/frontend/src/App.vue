<template>
  <div class="container">
    <h1>Group Project Demo</h1>
    
    <div class="task-form">
      <button @click="createTask">Add Task</button>
    </div>
    
    <div class="tasks">
      <div v-for="task in tasks" :key="task.id" class="task">
        Task {{ task.id }}: {{ task.status }}
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      tasks: []
    }
  },
  async mounted() {
    await this.refreshTasks()
    setInterval(() => this.refreshTasks(), 2000)
  },
  methods: {
    async createTask() {
      await axios.post('http://localhost:8000/tasks/')
      await this.refreshTasks()
    },
    async refreshTasks() {
      const response = await axios.get('http://localhost:8000/tasks/1')
      this.tasks = [response.data]
    }
  }
}
</script>

<style>
.container { max-width: 600px; margin: 50px auto; padding: 20px; }
.task-form button { padding: 10px 20px; background: #42b983; color: white; border: none; border-radius: 5px; }
.task { margin: 10px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }
</style>
