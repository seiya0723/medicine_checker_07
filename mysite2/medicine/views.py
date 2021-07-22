from django.shortcuts import render,redirect
from django.views import View

#クエリビルダ(複雑な検索処理を行う事ができる)
from django.db.models import Q

#JavaScript用にJSONレスポンスを返す
from django.http.response import JsonResponse

#レンダリングした後、文字列型にして返す
from django.template.loader import render_to_string


from .models import Medicine


#正規表現を使うので、インポート
import re

class IndexView(View):

    def get(self, request, *args, **kwargs):
        
        medicines   = Medicine.objects.all().count()
        print(medicines)

        #何も書かれていない医薬品の炙り出し。
        medicines   = Medicine.objects.filter(effect="",caution="",dosage="",side_effect="")
        print(len(list(medicines.values())))
        medicines.delete()

        #医薬品の開発会社が違うだけで中身は同じ(「」、［］で囲まれた部分を除外し、比較。一致しているものを表示もしくは削除する。)
        #改名していないので、後の処理で不一致になってしまっている。
        medicines   = Medicine.objects.all().order_by("name")

        counter     = 0
        old_name    = ""
        id_list     = []

        for medicine in medicines:
            new_name    = medicine.name
            #print("変更前:" + new_name)

            new_name    = re.sub("「.*」","",new_name)
            #print("変更後:" + new_name)
            
            #改名処理
            medicine.name   = new_name
            medicine.save()


            if old_name == new_name:
                counter += 1
                id_list.append(medicine.id)

            old_name    = new_name

        print("重複している数" + str(counter))

        #約22200行 → 重複と説明なしの医薬品除外 → 約9400行
        #Herokuの運用も可能になる。

        medicines   = Medicine.objects.filter(id__in=id_list)
        print(len(list(medicines.values())))
        medicines.delete()


        #mg単位の除外,mg以外にも%やg、μgにも対応
        medicines   = Medicine.objects.all().order_by("name")
        counter   = 0
        old_name    = ""
        id_list     = []

        for medicine in medicines:
            new_name    = medicine.name
            #print("変更前:" + new_name)

            new_name    = re.sub("\d+(\.|．)*\d*(mg|ｍｇ|g|ｇ|%|％|ml|ｍｌ|mL|ｍＬ|mg/mL|μg|μg/mL|ＭＢｑ)","",new_name)
            #print("変更後:" + new_name)

            #改名処理
            medicine.name   = new_name
            medicine.save()


            if old_name == new_name:
                counter += 1
                id_list.append(medicine.id)

            old_name    = new_name

        print("重複している数" + str(counter))
        medicines   = Medicine.objects.filter(id__in=id_list)
        print(len(list(medicines.values())))
        medicines.delete()



        #FIXME:薬品の量が違う場合、それが説明文に含まれている時、不一致で削除されない問題がある。
        medicines   = Medicine.objects.all().order_by("name")

        old = { "effect"     :"",
                "caution"    :"",
                "dosage"     :"",
                "side_effect":"",
                }
        counter = 0
        id_list = []

        for medicine in medicines:

            if old["effect"] == medicine.effect and old["caution"] == medicine.caution and old["dosage"] == medicine.dosage and old["side_effect"] == medicine.side_effect:
                counter += 1
                id_list.append(medicine.id)

            old["effect"]       = medicine.effect
            old["caution"]      = medicine.caution
            old["dosage"]       = medicine.dosage
            old["side_effect"]  = medicine.side_effect

        print("名前以外の全ての項目完全一致での重複数")
        print(counter)


        medicines   = Medicine.objects.filter(id__in=id_list)
        print(len(list(medicines.values())))
        medicines.delete()










        return render(request,"medicine/index.html")

index   = IndexView.as_view()


#Jsonでレスポンスを返す。
class SearchView(View):

    def get(self, request, *args, **kwargs):

        json    = {"error":True}

        if "search" in request.GET:

            #(1)キーワードが空欄もしくはスペースのみの場合、ページにリダイレクト
            if request.GET["search"] == "" or request.GET["search"].isspace():

                #リダイレクトではなくAjaxで送信されているのでjsonで返す。
                #return redirect("medicine:index")
                return JsonResponse(json)

            #チェックボックスがいずれも押されていない場合検索しない(全件出力され、処理が遅くなる)
            if "name" not in request.GET and "effect" not in request.GET and "caution" not in request.GET and "dosage" not in request.GET and "side_effect" not in request.GET:

                #リダイレクトではなくAjaxで送信されているのでjsonで返す。
                #return redirect("medicine:index")
                return JsonResponse(json)


            #(2)キーワードをリスト化させる(複数指定の場合に対応させるため)
            search      = request.GET["search"].replace("　"," ")
            search_list = search.split(" ")

            #(3)クエリを作る
            query       = Q()
            for word in search_list:
                if word == "":
                    continue

                #TIPS:AND検索の場合は&を、OR検索の場合は|を使用する。
                if "name"        in request.GET:
                    query |= Q(name__contains=word)

                if "effect"      in request.GET:
                    query |= Q(effect__contains=word)

                if "caution"     in request.GET:
                    query |= Q(caution__contains=word)

                if "dosage"      in request.GET:
                    query |= Q(dosage__contains=word)

                if "side_effect" in request.GET:
                    query |= Q(side_effect__contains=word)

            #(4)作ったクエリを実行
            medicines   = Medicine.objects.filter(query)
        else:
            medicines   = []

        context = { "medicines":medicines }

        #検索結果のレンダリングを文字列型にして返す。
        content = render_to_string("medicine/search.html",context,request)

        #エラーフラグをFalseにして、検索結果のHTML(文字列型)のデータをJSON形式でレスポンス、JSに引き渡す。
        json["error"]   = False
        json["content"] = content

        return JsonResponse(json)


search  = SearchView.as_view()
    

#テーブルにスタックする時、医薬品単体のデータを返す。
class SingleView(View):

    def get(self, request, pk, *args, **kwargs):
        print("single")
        json    = { "error":True }

        #pkから医薬品情報一件を抜き取る、JSONで返すので辞書型に書き換え。
        medicine    = Medicine.objects.filter(id=pk).first()

        #医薬品情報が無い場合はエラーを返す。
        if not medicine:
            return JsonResponse(json)

        
        #json形式で送信できるように辞書型に変換する
        dic = {}
        dic["name"]         = medicine.name
        dic["effect"]       = medicine.effect     
        dic["caution"]      = medicine.caution    
        dic["dosage"]       = medicine.dosage     
        dic["side_effect"]  = medicine.side_effect


        json["error"]       = False
        json["medicine"]    = dic

        return JsonResponse(json)


single  = SingleView.as_view()
