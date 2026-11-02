package mt.nativeaddon

import android.content.Context
import android.widget.ArrayAdapter
import android.widget.Spinner

/** UI-only symbol selection. Never changes broker positions or sends orders. */
class BbmaSymbolSelector(context:Context, symbols:List<String>, onSelected:(String)->Unit):Spinner(context) {
 private val available=SymbolCatalog.options(symbols)
 init {
  adapter=ArrayAdapter(context,android.R.layout.simple_spinner_dropdown_item,available.map{it.code})
  contentDescription="BBMA dashboard research symbol"
  onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener {
   override fun onNothingSelected(parent:android.widget.AdapterView<*>?){}
   override fun onItemSelected(parent:android.widget.AdapterView<*>?,view:android.view.View?,position:Int,id:Long){
    available.getOrNull(position)?.let{onSelected(it.code)}
   }
  }
 }
}
