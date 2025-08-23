package org.custom.slide

import androidx.compose.runtime.*
import android.util.Log

// Full credit for this snippet goes to Sean McQuillan - https://twitter.com/objcode
// Note the inline function below which ensures that this function is essentially
// copied at the call site to ensure that its logging only recompositions from the
// original call site.
class Debug(val tag: String = "ComposeApp") {
	@Composable
	inline fun Log(obj: Any, crossinline callback: (Any) -> String = { it as String }){
	    var compositionCount = remember { 0 }
		SideEffect {
			Log.d(tag, "${callback(obj)} compositions: ${++compositionCount}")
		}
	}
}
