package org.custom.slide

import org.jetbrains.compose.resources.DrawableResource
import org.jetbrains.compose.resources.painterResource
import org.jetbrains.compose.ui.tooling.preview.Preview
import org.jetbrains.annotations.Debug

import androidx.compose.runtime.*
import androidx.compose.runtime.snapshots.SnapshotStateList
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.Alignment
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.safeContentPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material3.Icon
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text

@Composable
@Preview
fun App() {
    MaterialTheme {
        val debugImage = Debug()
        val context = LocalContext.current
        val images: SnapshotStateList<DrawableRes> = remember {
            mutableStateListOf<DrawableRes>()
        }
        val photoPicker = PhotoPicker().apply {
            setup {
                images.apply {
                    addAll(size,it)
                }
            }
        }
        val pagerState = rememberPagerState(pageCount = {
            images.size+1
        })

        HorizontalPager(
            state = pagerState,
            modifier = Modifier.fillMaxSize(),
        ) { page ->
            //debugImage.Log("image $page: ${images[page].res}")
            if (page == images.size) {
                Button(
                    onClick = {
                        photoPicker.launch()
                    },
                    modifier = Modifier.fillMaxSize()
                ) {
                    Icon(
                        Icons.Rounded.Add,
                        contentDescription = "Add an image",
                        modifier = Modifier
                            .size(width = 100.dp, height = 100.dp)
                            .align(Alignment.CenterVertically)
                    )
                }
            }
            else {
                photoPicker.SelectedImageItem(images[page])
            }
        }
    }
}
