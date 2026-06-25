import axios from 'axios';
const apiClient = axios.create({ baseURL: '/' });

export default {
  getEvaluation(threadId, platform, sourceFile) {
    return apiClient.get(`/evaluate-thread/${threadId}`, { 
      params: { platform, source_file: sourceFile } 
    });
  }
}