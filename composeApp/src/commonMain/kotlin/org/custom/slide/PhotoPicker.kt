package org.custom.slide

import androidx.compose.runtime.*
import coil3.compose.LocalPlatformContext
import coil3.compose.AsyncImage
import coil3.request.ImageRequest


interface DrawableRes {
    val data: Any
    val desc: String
}
expect class PhotoPicker() {
    @Composable
    fun setup(callback: (List<DrawableRes>) -> Unit)
    fun launch()
}
@Composable
fun PhotoPicker.SelectedImageItem(res: DrawableRes) {
    val context = LocalPlatformContext.current
    AsyncImage(
        model = ImageRequest.Builder(context)
            .data(res.data)
            .build(),
        contentDescription = res.desc,
    )
}
