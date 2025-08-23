package org.custom.slide

import androidx.compose.runtime.*

import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.ManagedActivityResultLauncher
import androidx.activity.compose.setContent
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts

import android.net.Uri


class AndroidDrawableRes(override val data: Uri, override val desc: String) : DrawableRes
actual class PhotoPicker {
    lateinit private var multipleImagePickerLauncher: ManagedActivityResultLauncher<PickVisualMediaRequest, List<Uri>>

    @Composable
    actual fun setup(callback: (List<DrawableRes>) -> Unit) {
        multipleImagePickerLauncher = rememberLauncherForActivityResult(
            contract = ActivityResultContracts.PickMultipleVisualMedia(),
            onResult = {
                callback (
                    it.map {
                        AndroidDrawableRes(it, "Image")
                    }
                )
            },
        )
    }
    actual fun launch() {
        multipleImagePickerLauncher.launch(
            PickVisualMediaRequest(
                ActivityResultContracts.PickVisualMedia.ImageOnly
            )
        )
    }
}
