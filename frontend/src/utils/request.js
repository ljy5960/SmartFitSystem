import axios from 'axios';
import { ElMessage } from 'element-plus';

const service = axios.create({
  baseURL: process.env.VUE_APP_BASE_API || 'http://127.0.0.1:5000',
  timeout: 10000
});
service.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers['Authorization'] = 'Bearer ' + token;
  }
  return config;
}, error => {
  return Promise.reject(error);
});
service.interceptors.response.use(response => {
  return response;
}, error => {
  ElMessage.error(error.response?.data?.msg || '网络请求失败');
  return Promise.reject(error);
});
export default service;