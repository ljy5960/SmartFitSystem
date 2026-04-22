import axios from 'axios';
import { ElMessage } from 'element-plus';

// 1. 创建 axios 实例
const service = axios.create({
  // 如果有环境变量则用环境变量，否则用本地地址
  baseURL: process.env.VUE_APP_BASE_API || 'http://127.0.0.1:5000',
  timeout: 10000 // 超时时间 10 秒
});

// 2. 请求拦截器：每次发请求前自动带上 token
service.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers['Authorization'] = 'Bearer ' + token;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

// 3. 响应拦截器：统一处理报错
service.interceptors.response.use(response => {
  return response;
}, error => {
  ElMessage.error(error.response?.data?.msg || '网络请求失败');
  // 如果是 401 token 过期，可以在这里自动跳转登录页
  return Promise.reject(error);
});

export default service;