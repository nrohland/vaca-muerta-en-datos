import {defineConfig} from '@playwright/test';
const port=Number(process.env.ESTRATO_TEST_PORT??4173);
export default defineConfig({testDir:'./tests',testMatch:'*.spec.ts',use:{baseURL:`http://127.0.0.1:${port}`,headless:true},webServer:{command:`PORT=${port} node tests/serve.mjs`,url:`http://127.0.0.1:${port}/vaca-muerta-pulse/`,reuseExistingServer:false},reporter:'list'});
