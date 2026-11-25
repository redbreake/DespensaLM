package com.example.ui.components

import android.annotation.SuppressLint
import android.util.Log
import android.view.ViewGroup
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

@SuppressLint("UnsafeOptInUsageError")
@Composable
fun BarcodeScannerView(
    onBarcodeScanned: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val cameraProviderFuture = remember { ProcessCameraProvider.getInstance(context) }

    // Maintain analyzer executor and ML Kit scanner client with proper lifecycle cleanup
    val cameraExecutor: ExecutorService = remember { Executors.newSingleThreadExecutor() }
    val barcodeScanner = remember { BarcodeScanning.getClient() }
    val currentOnBarcodeScanned by rememberUpdatedState(onBarcodeScanned)
    var previewViewRef by remember { mutableStateOf<PreviewView?>(null) }

    // Throttle scan rate to prevent rapid duplicate scanner pulses
    var lastScannedTime by remember { mutableLongStateOf(0L) }

    DisposableEffect(Unit) {
        onDispose {
            try {
                if (cameraProviderFuture.isDone) {
                    cameraProviderFuture.get().unbindAll()
                }
            } catch (exc: Exception) {
                Log.w("BarcodeScannerView", "Error unbinding camera on dispose", exc)
            }
            barcodeScanner.close()
            cameraExecutor.shutdown()
        }
    }

    LaunchedEffect(previewViewRef, lifecycleOwner) {
        val previewView = previewViewRef ?: return@LaunchedEffect
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.surfaceProvider = previewView.surfaceProvider
            }

            val imageAnalysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()

            imageAnalysis.setAnalyzer(cameraExecutor) { imageProxy ->
                val mediaImage = imageProxy.image
                if (mediaImage != null) {
                    val image = InputImage.fromMediaImage(
                        mediaImage,
                        imageProxy.imageInfo.rotationDegrees
                    )

                    barcodeScanner.process(image)
                        .addOnSuccessListener { barcodes ->
                            for (barcode in barcodes) {
                                val rawValue = barcode.rawValue
                                if (!rawValue.isNullOrBlank()) {
                                    val now = System.currentTimeMillis()
                                    if (now - lastScannedTime > 2000) { // 2s scanning throttle
                                        lastScannedTime = now
                                        previewView.post {
                                            currentOnBarcodeScanned(rawValue)
                                        }
                                    }
                                }
                            }
                        }
                        .addOnFailureListener {
                            Log.e("BarcodeScannerView", "Error scanning frame: ", it)
                        }
                        .addOnCompleteListener {
                            imageProxy.close()
                        }
                } else {
                    imageProxy.close()
                }
            }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    lifecycleOwner,
                    cameraSelector,
                    preview,
                    imageAnalysis
                )
            } catch (exc: Exception) {
                Log.e("BarcodeScannerView", "Use case binding failed", exc)
            }
        }, ContextCompat.getMainExecutor(context))
    }

    AndroidView(
        factory = { ctx ->
            PreviewView(ctx).apply {
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )
                scaleType = PreviewView.ScaleType.FILL_CENTER
            }.also { previewViewRef = it }
        },
        modifier = modifier.fillMaxSize()
    )
}
