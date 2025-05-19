# 資料標註原則
資料集一共分成7類：
```yaml
  '1': OK 
  '2': IMMATURE         #銀皮(要覆蓋到整個都是才算)
  '3': LOOKS_WEIRD      #表面瑕疵(看起來有問題就算)
  '4': INSECT_DAMAGE    #蟲害(表面有洞的)
  '5': BROKEN           #形狀不對
  '6': OVERLAPPED       #重疊(畫面中有多顆咖啡豆)
  '7': OTHER            #其他(不是咖啡豆的東西)
  '8': LOTTERY          #長得醜醜的，但還是可以用的咖啡豆
```
左邊1~8表示在標註程式中按下對應按鍵會標註的類型
序號越大的表示優先序越高，如果遇到有問題的豆子優先以該級別標註
比如同時破損與蟲害，那麼就優先標註破損

# OK
OK類別定義很廣泛
最標準的OK應該像這樣，應該有點偏向翡翠的顏色，但可能因為光照環境不同而不同
![picture 39](https://i.imgur.com/11p9QUF.png)  
以下是範例
![picture 0](https://i.imgur.com/LNY6Cog.png)  
![picture 1](https://i.imgur.com/JgUelRZ.png)  
![picture 2](https://i.imgur.com/SsirorT.png)  

# IMMATURE
針對銀皮，如果畫面占比不超過10%的銀皮，則一樣當作OK
![picture 7](https://i.imgur.com/0bpFgU2.png)  

底下這種就直接當作銀皮類別
![picture 3](https://i.imgur.com/tG7WURS.png)  
![picture 4](https://i.imgur.com/9D6DcRM.png)  
![picture 5](https://i.imgur.com/w72jiDE.png)  
![picture 6](https://i.imgur.com/kextFqV.png)  
![picture 8](https://i.imgur.com/z8mjCBm.png)  

如果有混合其他類別的，也要標註銀皮


# LOOKS_WEIRD(表面瑕疵)
這個分類主要處理**會影響咖啡風味的**豆子
只要顏色明顯往褐色偏，就算是一種瑕疵(輕微腐敗)
![picture 25](https://i.imgur.com/Wkg1AqI.png)  

如果有明顯色塊不同，也算是一種瑕疵
包括忽然出現咖啡色塊(可能是凋零、真菌)、黑色塊(發霉)都算這種
![picture 14](https://i.imgur.com/2lrUZP4.png)  
![picture 17](https://i.imgur.com/D8WobrS.png)  
![picture 41](https://i.imgur.com/M02B4By.png)  
![picture 42](https://i.imgur.com/JeleXVL.png)  
![picture 43](https://i.imgur.com/pJMC9dE.png)  


長得不可名狀的也是這類(有時候會合併銀皮特徵與BROKEN特徵)
![picture 35](https://i.imgur.com/p8tmeb6.png)  
![picture 40](https://i.imgur.com/0KBbHKQ.png)  



# BROKEN
只要形狀錯誤就算
無論是邊緣錯誤，或是表面形狀不正確都算，貝殼豆也算這類

邊緣錯誤例子：
![picture 11](https://i.imgur.com/QzcAzKk.png)  
![picture 16](https://i.imgur.com/PA2EQPQ.png)  
![picture 19](https://i.imgur.com/pr49GXY.png)  
![picture 20](https://i.imgur.com/N189dJy.png)  
![picture 21](https://i.imgur.com/8MfhytK.png)  
![picture 22](https://i.imgur.com/8jFBljv.png)  

表面形狀不正確例子：
![picture 12](https://i.imgur.com/yJC9enp.png)  
![picture 13](https://i.imgur.com/iddB6Uk.png)  
![picture 23](https://i.imgur.com/lv351tR.png)  

都不正確的例子：
![picture 18](https://i.imgur.com/gmaQgLE.png)  
![picture 29](https://i.imgur.com/X1ypOdy.png)  
![picture 37](https://i.imgur.com/gxQ7IMW.png)  
![picture 38](https://i.imgur.com/eGwhnRP.png)  

# INSECT_DAMAGE
只要圖片上有一個明顯黑點就算
![picture 9](https://i.imgur.com/lXy7bsP.png)  
![picture 34](https://i.imgur.com/3jp9GpG.png)  
如果有好幾個點當然也算這類
![picture 36](https://i.imgur.com/QaGq0Hx.png)  

如果是出現在邊緣，也算蟲害
豆子的蟲害點出現在豆子的邊緣處非常常見，所以這邊可以判斷嚴格一點，只要看起來有就可以算
![picture 15](https://i.imgur.com/FahwZMN.png)  
![picture 24](https://i.imgur.com/kcsCBmL.png)  
![picture 32](https://i.imgur.com/TVMMn1m.png)  

# OVERLAPPED
複數顆豆子同時出現，我猜不用我多解釋?

# OTHER
明顯不是咖啡豆的東西，比如碎塊、殘渣、麻線殘渣、或是因為影像處理物檢測沒濾掉的東西
![picture 30](https://i.imgur.com/iLNARy7.png)  
![picture 31](https://i.imgur.com/1eoKq3e.png)  
![picture 33](https://i.imgur.com/7t2gnTB.png)  

# LOTTERY
長得醜醜的，但沒有明顯瑕疵，只是長得醜而已
比如：表面刮傷、形狀長得不標準(但還不算破掉)
如果看起來是豆子內部發黑，算是發霉豆，就不算在這類
但如果是表面有一點淺淺的黑色，那其實就算刮傷，就算這類

![alt text](../images/image.png)
![圖 1](../images/d1f6f28336fd0f607261a411d23904bb9a1fa7116ffe4f5d9be3f5e6e09fce11.png)  
![圖 2](../images/b2395b1f27db59fd224535b18e9922447cf3a2db93b17afdeb8cdc882f2265f0.png)  
![圖 3](../images/6e34e02ba78197db39f6962b57d39f69ab2aa5b36527d8ed66c0c1a2db7536bc.png)  
![圖 4](../images/5a9a111fe10d5aa68e1e694c5a05240b9fc1d6c00260887d700cfa185397268a.png)  
