using System;
using System.Linq.Expressions;
class Item { public bool Enabled { get; set; } }
class Fixture {
 static Expression<Func<Item,bool>> Property() {
  var item=Expression.Parameter(typeof(Item),"item");
  return Expression.Lambda<Func<Item,bool>>(Expression.Property(item,typeof(Item).GetMethod("get_Enabled")),new[]{item});
 }
 static Expression<Func<int,int,int>> Block() {
  var left=Expression.Parameter(typeof(int),"left");
  var right=Expression.Parameter(typeof(int),"right");
  return Expression.Lambda<Func<int,int,int>>(Expression.Block(Expression.Add(left,right)),new[]{left,right});
 }
 static Expression<Func<int,bool>> Supported() { return value=>value>3; }
 static int Main() {
  try { return Run(); } catch(Exception error) { Console.Error.WriteLine(error.GetType().Name+": "+error.Message); return 1; }
 }
 static int Run() {
  var property=Property();
  if(property.Parameters[0].Name!="item" || !object.ReferenceEquals(((MemberExpression)property.Body).Expression,property.Parameters[0])) throw new Exception("Property parameter identity changed");
  var read=property.Compile();
  if(read(new Item()) || !read(new Item{Enabled=true})) throw new Exception("Property behavior changed");
  var block=Block();
  if(block.Parameters[0].Name!="left" || block.Parameters[1].Name!="right" || block.Compile()(4,7)!=11) throw new Exception("Block parameters changed");
  var supported=Supported().Compile();
  if(supported(3) || !supported(4)) throw new Exception("Supported lambda changed");
  Console.WriteLine("PASS: fallback parameter initialization, identity, multiple parameters and supported lambdas");
  return 0;
 }
}
