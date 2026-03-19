import os
from sklearn.model_selection import StratifiedKFold
import shutil
import subprocess
import numpy as np
import pandas as pd
import pywt
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def extract_dwt_features(csv_path):
    df = pd.read_csv(csv_path)
    
    t = df['Timestamp_ms'].values
    if len(t) < 2:
        return None
            
    wavelet = 'db8'
    
    features = []
    
    # The Raw Channels: CH1, CH2, CH3, CH4
    ch1 = df['CH1_V'].values if 'CH1_V' in df.columns else np.zeros(len(df))
    ch2 = df['CH2_V'].values if 'CH2_V' in df.columns else np.zeros(len(df))
    ch3 = df['CH3_V'].values if 'CH3_V' in df.columns else np.zeros(len(df))
    ch4 = df['CH4_V'].values if 'CH4_V' in df.columns else np.zeros(len(df))
    
    signals_to_process = [ch1, ch2, ch3, ch4]
            
    for signal in signals_to_process:
        signal = signal - np.mean(signal)
            
        coeffs = pywt.wavedec(signal, wavelet, level=5)
    
        band_features = [np.mean(c**2) for c in coeffs]
        
        features.extend(band_features)
            
    return np.array(features)

def load_all_segments(base_dir):
    X = []
    y = []
    
    terrain_folders = sorted([
        d for d in base_dir.iterdir()
        if d.is_dir() and (d / "rotations").exists()
    ])
    
    for terrain_dir in terrain_folders:
        folder_name = terrain_dir.name
        rotations_dir = terrain_dir / "rotations"
        
        csv_files = sorted([f for f in os.listdir(rotations_dir) if f.endswith(".csv")])
        
        for csv_file in csv_files:
            csv_path = rotations_dir / csv_file
            features = extract_dwt_features(csv_path)
            if features is not None:
                X.append(features)
                y.append(folder_name)
    
    return np.array(X), np.array(y)

def main():
    base_dir = Path(__file__).parent
    k = 3  # Number of folds
    
    print("Loading ALL rotation segments and extracting DWT features...")
    X_all, y_all = load_all_segments(base_dir)
    print(f"Total samples: {len(X_all)}")
    
    classes = sorted(list(set(y_all)))
    print(f"Classes ({len(classes)}): {classes}\n")
    
    skf = StratifiedKFold(n_splits=k, shuffle=True)
    
    fold_accuracies = []
    all_y_true = []
    all_y_pred = []
    
    print(f"Running {k}-fold stratified cross-validation...\n")
    
    for fold, (train_indices, test_indices) in enumerate(skf.split(X_all, y_all)):
        X_train = X_all[train_indices]
        y_train = y_all[train_indices]
        X_test = X_all[test_indices]
        y_test = y_all[test_indices]
        
        print(f"  Fold {fold + 1}/{k}:")
        for cls in classes:
            n_train = np.sum(y_train == cls)
            n_test = np.sum(y_test == cls)
            print(f"    {cls}: {n_train} train, {n_test} test")
        
        clf = make_pipeline(StandardScaler(), RandomForestClassifier(n_estimators=100))
        clf.fit(X_train, y_train)
        
        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        fold_accuracies.append(acc)
        
        all_y_true.extend(y_test)
        all_y_pred.extend(y_pred)
        
        print(f"    Accuracy = {acc:.2%}\n")
    
    mean_acc = np.mean(fold_accuracies)
    std_acc = np.std(fold_accuracies)
    
    print(f"\n{'='*50}")
    print(f"K-Fold Cross-Validation Results ({k} folds)")
    print(f"{'='*50}")
    print(f"  Mean Accuracy: {mean_acc:.2%}")
    print(f"  Std Deviation: {std_acc:.2%}")
    print(f"  Min Accuracy:  {min(fold_accuracies):.2%}")
    print(f"  Max Accuracy:  {max(fold_accuracies):.2%}")
    
    print(f"\nAggregated Classification Report (across all {k} folds):")
    print(classification_report(all_y_true, all_y_pred, labels=classes, zero_division=0))
    
    cm = confusion_matrix(all_y_true, all_y_pred, labels=classes)
    
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    import matplotlib.image as mpimg

    plt.figure(figsize=(14, 12))
    ax = sns.heatmap(cm, annot=True, fmt='d', cmap='Purples', 
                xticklabels=classes, yticklabels=classes,
                cbar_kws={'label': f'Number of Segments (Aggregated over {k} folds)'})
                
    plt.title(f'Terrain Classification Confusion Matrix\n({k}-Fold Cross-Validation, Random Forest)', fontweight="bold", pad=20)
    plt.ylabel('True Terrain Label', fontweight="bold", labelpad=80) 
    plt.xlabel('Predicted Terrain Label', fontweight="bold", labelpad=80) 
    
    plt.xticks(rotation=45, ha='right')
    ax.tick_params(axis='y', pad=70)
    ax.tick_params(axis='x', pad=70)
    
    def add_image_to_axis(ax, class_name, x, y, is_xaxis=False):
        img_path = base_dir / class_name / "img.png"
        if img_path.exists():
            try:
                img = mpimg.imread(str(img_path))
                imagebox = OffsetImage(img, zoom=0.08) 
                
                if is_xaxis:
                    ab = AnnotationBbox(imagebox, (x, y),
                                        xybox=(0, -35),
                                        xycoords=('data', 'axes fraction'),
                                        boxcoords="offset points",
                                        box_alignment=(0.5, 0.5),
                                        frameon=False)
                else:
                    ab = AnnotationBbox(imagebox, (x, y),
                                        xybox=(-35, 0),
                                        xycoords=('axes fraction', 'data'),
                                        boxcoords="offset points",
                                        box_alignment=(0.5, 0.5),
                                        frameon=False)
                ax.add_artist(ab)
            except Exception as e:
                pass
                
    for i, label in enumerate(ax.get_yticklabels()):
        add_image_to_axis(ax, label.get_text(), 0, i + 0.5, is_xaxis=False)
        
    for i, label in enumerate(ax.get_xticklabels()):
        add_image_to_axis(ax, label.get_text(), i + 0.5, 0, is_xaxis=True)
    
    plt.subplots_adjust(left=0.25, bottom=0.25)
    
    cm_path = base_dir / "wavelet_kfold_confusion_matrix.png"
    plt.savefig(str(cm_path), dpi=150, bbox_inches="tight")
    print(f"\nSaved aggregated confusion matrix to {cm_path}")

if __name__ == "__main__":
    main()
