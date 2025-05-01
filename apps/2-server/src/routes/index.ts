
import express from 'express';
import * as authController from '../controllers/authController';
import * as fileController from '../controllers/fileController';
import * as gatewayController from '../controllers/gatewayController';

import { auth } from '../middlewares/auth';
import { upload } from '../middlewares/upload';

const router = express.Router();

// Auth routes
router.post('/auth/register', authController.register);
router.post('/auth/login', authController.login);
router.get('/auth/me', auth, authController.getCurrentUser);

// File routes
router.post('/files/upload', auth, upload.single('file'), fileController.uploadFile);
router.get('/files', auth, fileController.getFiles);
router.get('/files/:id', auth, fileController.getFileAnalysis);
router.delete('/files/:id', auth, fileController.deleteFile);

// Advanced File routes
router.get('/files/:id/insights', auth, fileController.getFileInsights)
router.get('/files/:id/visualizations', auth, fileController.getFileVisualizations)

// Gateway routes - Analysis API
router.post('/analyze{/*path}', auth, gatewayController.proxyAnalyzeRequest);

// Gateway routes - Chat API
router.all('/chat{/*path}', auth, gatewayController.proxyChatRequest);

// Health check
router.get('/health', gatewayController.proxyHealthCheckRequest);

export default router;