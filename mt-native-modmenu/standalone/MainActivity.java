package com.msa.mt5research;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.view.Gravity;
import android.widget.FrameLayout;
import android.widget.TextView;
import mt.nativeaddon.Mt5ResearchMenu;

/** Standalone offline research shell; not MetaTrader or a brokerage client. */
public final class MainActivity extends Activity implements Mt5ResearchMenu.Listener {
    private Mt5ResearchMenu menu;
    private TextView status;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(11, 19, 33));
        TextView heading = new TextView(this);
        heading.setText("MSA CHART RESEARCH\nOffline research workspace\nNo broker connection or trading");
        heading.setTextColor(Color.WHITE);
        heading.setTextSize(18);
        heading.setPadding(24, 24, 24, 24);
        root.addView(heading, new FrameLayout.LayoutParams(-1, -2, Gravity.TOP));
        status = new TextView(this);
        status.setText("No market data loaded. Controls are research preferences only.");
        status.setTextColor(Color.rgb(175, 207, 237));
        status.setPadding(24, 12, 24, 32);
        FrameLayout.LayoutParams bottom = new FrameLayout.LayoutParams(-1, -2, Gravity.BOTTOM);
        root.addView(status, bottom);
        setContentView(root);
        menu = new Mt5ResearchMenu(this, this);
        menu.attach(root);
    }
    @Override public void onLayerChanged(String layer, boolean enabled) {
        status.setText(layer + (enabled ? " enabled" : " disabled") + " (no chart data loaded)");
    }
    @Override public void onAction(String action) {
        status.setText(action + " unavailable until an offline dataset is imported.");
    }
    @Override protected void onDestroy() {
        if (menu != null) menu.detach();
        super.onDestroy();
    }
}
